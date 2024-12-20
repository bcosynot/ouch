from fastapi import FastAPI
import uvicorn
from pydantic_settings import BaseSettings
from sqlite3 import connect, Error as SQLiteError
import httpx
import os
import random
import asyncio



def validate_settings():
    print("Validating settings")
    missing_keys = []
    if not settings.ow_api_key:
        missing_keys.append("ow_api_key")
    if not settings.lat:
        missing_keys.append("lat")
    if not settings.lon:
        missing_keys.append("lon")

    if missing_keys:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")

# Pydantic Settings Configuration
class Settings(BaseSettings):
    ow_api_key: str
    db_path: str = "data/data.db"
    lat: float
    lon: float

    class Config:
        env_file = ".env"
        env_prefix = "OUCH_"


settings = Settings()


validate_settings()

print("Starting server")

app = FastAPI()

async def get_weather_data(api_key: str, lat: float, lon: float, exclude: str = "minutely,hourly,daily,alerts") -> dict:
    """
    Fetches weather data asynchronously from the OpenWeatherMap API.

    This function retrieves weather data based on the provided latitude and longitude
    coordinates. It allows customization of the data retrieved by specifying which
    parts of the weather data to exclude. If the API key is invalid or not provided,
    the function raises an error. It implements retry logic with exponential backoff
    to handle transient errors and API rate limiting.

    :param api_key: A string representing the API key required to authenticate
                    the request to the OpenWeatherMap API.
    :param lat: A float representing the latitude of the location for which
                weather data is desired.
    :param lon: A float representing the longitude of the location for which
                weather data is desired.
    :param exclude: A string specifying parts of the weather data to exclude
                    (default is "minutely,hourly,daily,alerts").
    :return: A dictionary containing the weather data retrieved from the API.

    :raises ValueError: If the API key is not provided.
    :raises RuntimeError: If the API call fails after all retries or the API rate
                          limit is exceeded.
    """
    if not api_key:
        raise ValueError("API key is required.")

    retries = 5
    backoff = 1  # initial backoff duration in seconds
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        for attempt in range(1, retries + 1):
            try:
                response = await client.get(
                    "https://api.openweathermap.org/data/3.0/onecall",
                    params={
                        "lat": lat,
                        "lon": lon,
                        "appid": api_key,
                        "units": "imperial",
                        "exclude": exclude
                    }
                )
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    raise RuntimeError("Too many requests - API rate limit reached. Please try again later.")
                else:
                    raise RuntimeError("Error fetching weather data from the API.")
            except httpx.RequestError as e:
                if attempt == retries:
                    raise RuntimeError(f"Request failed after {retries} retries: {e}")
                jitter = random.uniform(0, 0.5)  # adding a small random jitter
                await asyncio.sleep(backoff + jitter)
                backoff *= 2




def setup_database():
    """Ensure the database and table exist."""
    # Check if database file exists, create it if not
    if not os.path.exists(settings.db_path):
        try:
            os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
            open(settings.db_path, 'w').close()
        except OSError as os_error:
            raise RuntimeError(f"Error creating database file or directory: {os_error}")
    with connect(settings.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS owie_logs (
                weather_id INTEGER,
                weather_main TEXT,
                weather_description TEXT,
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_time INTEGER NOT NULL,
                body_part TEXT NOT NULL,
                humidity REAL NOT NULL,
                precipitation REAL NOT NULL,
                uv_index REAL NOT NULL,
                temperature REAL NOT NULL,
                pressure REAL NOT NULL
            )
            """
        )
        conn.commit()


def insert_owie_log(date_time: int, body_part: str, weather_data: dict):
    """Insert a new owie log into the database."""

    def execute_insert(db_cursor, db_connection):
        """Executes the INSERT query in the database."""
        db_cursor.execute(
            """
            INSERT INTO owie_logs (date_time, body_part, temperature, pressure, humidity, precipitation, uv_index, weather_id, weather_main, weather_description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (date_time, body_part, weather_data["temperature"], weather_data["pressure"],
             weather_data["humidity"], weather_data["precipitation"], weather_data["uv_index"],
             weather_data["weather_id"], weather_data["weather_main"], weather_data["weather_description"])
        )
        try:
            db_connection.commit()
        except SQLiteError as e:
            raise RuntimeError(f"Error while inserting data into the database: {e}")

    # Database connection and execution
    with connect(settings.db_path) as db_connection:
        db_cursor = db_connection.cursor()
        execute_insert(db_cursor, db_connection)


@app.get("/")
async def home():
    """
    Home endpoint to test API availability.
    """
    return {"message": "Hello World"}, 200


@app.post("/owie/{body_part}")
async def log_owie(body_part: str):
    """
    Logs an "owie" event, including weather data and body part information, to a database
    based on the provided inputs. Retrieves current weather data using an external API and
    links it to the reported "owie".

    The function first checks for missing required environment variables, which are necessary
    to interface with an external weather API and database. It then fetches weather data, ensures
    the completeness of the data, and logs the "owie" details into the database. If successful,
    it returns a confirmation message along with the logged data.

    :param body_part: The body part associated with the "owie" event.
    :type body_part: str
    :return: A dictionary containing a success message, the logged body part, temperature, and
        pressure or an error message and status if necessary data is missing.
    :rtype: dict
    :raises RuntimeError: If the weather data fetched from the external API is incomplete.
    """
    if not settings.ow_api_key or not settings.db_path or not settings.lat or not settings.lon:
        return {"error": "Missing required environment variables"}, 400

    weather_data = await get_weather_data(settings.ow_api_key, settings.lat, settings.lon)
    current_weather = weather_data.get("current", {})
    humidity = current_weather.get("humidity")
    precipitation = current_weather.get("rain", {}).get("1h", 0.0) or current_weather.get("snow", {}).get("1h", 0.0)
    uv_index = current_weather.get("uvi")
    weather_id = current_weather.get("weather", [{}])[0].get("id")
    weather_main = current_weather.get("weather", [{}])[0].get("main")
    weather_description = current_weather.get("weather", [{}])[0].get("description")
    temperature = current_weather.get("temp")
    pressure = current_weather.get("pressure")
    date_time = current_weather.get("dt")
    if temperature is None or pressure is None or date_time is None or humidity is None or uv_index is None or weather_id is None or weather_main is None or weather_description is None:
        raise RuntimeError("Incomplete weather data received from the API.")

    # Setup the database and insert a log
    setup_database()
    log_weather_data = {
        "weather_id": weather_id,
        "weather_main": weather_main,
        "weather_description": weather_description,
        "temperature": temperature,
        "pressure": pressure,
        "humidity": humidity,
        "precipitation": precipitation,
        "uv_index": uv_index,
    }
    insert_owie_log(date_time, body_part, log_weather_data)

    return {
        "message": "Logged owie details successfully",
        "body_part": body_part,
        "temperature": temperature,
        "pressure": pressure,
    }


def start():
    """
    Launched with `poetry run start` at root level.
    Starts the Uvicorn server to run the FastAPI application.
    """
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
