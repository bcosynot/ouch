# Ouch: Personal "Pain" Analytics for Weather-Linked Events

Ouch is a lightweight FastAPI-based Python application designed to log and analyze user-reported events ("owies" i.e., injuries, discomfort, etc.) linked with current weather conditions. It provides an easy way to track and correlate events with live environmental data, all while maintaining a minimal and reproducible infrastructure.

---

## Key Features
  
- **Event Logging with Weather Context:** 
  - Logs user-reported events ("owies") with associated weather data into an SQLite database for future analysis.

- **Reproducible Development Environment:**
  - Uses [Nix](https://nixos.org/) for completely reproducible builds via `flake.nix`.
  - Poetry is used to manage Python dependencies with version locks.

---

## Technologies Used

### Python Frameworks
- **FastAPI** (`^0.115.6`): A high-performance, Python-based API framework.
- **Pydantic-Settings** (`^2.7.0`): For easy configuration handling via environment variables.
- **Httpx** (`^0.28.1`): An HTTP client for making async requests to APIs like OpenWeatherMap.
- **SQLite**: A simple, lightweight database for event storage.

### Development Tools
- **Poetry** (`pyproject.toml`): Dependency and environment management.
- **Nix** (`flake.nix`): Reproducible build system ensuring consistent behavior across environments.

---

## Usage information

### 1. **Environmental Variables**
The application relies on `.env` files for environment-specific settings, such as:
- `OUCH_OW_API_KEY`: API Key for OpenWeatherMap (required).
- `OUCH_LAT`: Latitude of the desired location for weather data.
- `OUCH_LON`: Longitude of the desired location for weather data.
- `OUCH_DB_PATH`: (Default: `data/data.db`) Path to the SQLite database file.

These variables are loaded at runtime and validated upfront.

---

### 2. **Project Lifecycle**
- Main application is started via:
```bash
poetry run start
```
This runs a Uvicorn server hosting the FastAPI app.

- The application uses the `/data/data.db` file (or optional custom location) for database persistence, creating it dynamically if it doesn’t exist.

- For weather data retrieval, the app retries up to 5 times in case of network or API issues, incorporating exponential backoff with jitter for robustness.

#### **Using Nix**
This project includes a `flake.nix` for reproducible builds:
```bash
nix develop
```
This creates a development shell with exact dependencies (Python, Poetry, and application-specific modules).

To build and run the application package:
```bash
nix run
```

### **Using Poetry**
Alternatively, you can use Poetry to manage dependencies:

1. Install dependencies:
```bash
poetry install
```

1. Start the application:
```bash
poetry run start
```

---

## Example Workflow

1. **Start application**: Use `poetry run start` or `nix run` to launch the server.
2. **Log an event**:
    - Call `POST /owie/{body_part}` with your chosen body part.
    - The app retrieves relevant weather data, logs it alongside the event, and stores it in the database.
3. **Analyze logs**:
    - Query or export the SQLite database (`owie_logs` table) for further exploration.

---

## Contributing
Feel free to fork and submit pull requests if you’d like to improve upon or expand this project!

