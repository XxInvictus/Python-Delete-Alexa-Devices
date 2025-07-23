# Alexa Manager

A Python tool for managing Amazon Alexa devices, entities, and groups via the Alexa API. This project is structured for maintainability, testability, and clarity, following modern Python best practices.

## Project Structure

```
.
├── config/                # Configuration files (user_config.json, global_config.json)
├── src/
│   └── alexa_manager/     # Main source code (api.py, config.py, main.py, models.py, utils.py)
│       └── __init__.py
├── tests/                 # Unit and integration tests
├── requirements.txt       # (Optional) For legacy compatibility
├── pyproject.toml         # Project metadata and dependencies
├── uv.lock                # Locked dependencies (managed by uv)
├── README.md
└── LICENSE
```

## Installation

1. **Python Version:** Requires Python 3.13 or newer.
2. **Install dependencies using [uv](https://github.com/astral-sh/uv):**
   ```sh
   uv install
   uv sync
   ```
   Or, to use the lockfile:
   ```sh
   uv sync --use-lock
   ```
   > **Note:** `uv` installs in editable mode by default. Use only native `uv` commands for dependency management. Avoid using `uv pip` except for legacy compatibility.

## Configuration

- All configuration files are in the `config/` directory.
- On first run, `user_config.json` is created from `global_config.json` if it does not exist.
- You must fill in your Amazon Alexa API credentials and other required values in `config/user_config.json`.
- See comments in the config files for details on each field.

## How to Retrieve Required Configuration Values (Android/iOS)

To use this tool, you need to extract certain authentication values from the Alexa app on your mobile device. Follow these steps:

1. **Download and install an HTTP Sniffer on your device.**
   - For iOS: [HTTP Catcher](https://apps.apple.com/de/app/http-catcher/id1445874902) or [Proxyman](https://apps.apple.com/us/app/proxyman-network-debug-tool/id1551292695).
   - For Android: [HTTP Toolkit](https://httptoolkit.tech/) (requires root or WSA workaround; see below).
   - For Android, if your device is not rooted, you can use Windows Subsystem for Android (WSA) with Magisk and Google apps. See online guides for setup details.
   - Note: For Android, you must install the sniffer's certificate on your device. Proxy-based sniffers will not work due to certificate pinning in the Alexa app.
2. **Open the Alexa app and log in with the account you want to manage.**
3. **Navigate to the Devices tab.**
4. **Start a new capture in the HTTP Sniffer.**
5. **Refresh the device list in the Alexa app by pulling down.**
6. **Let the page load completely.**
7. **Delete a device using the Alexa app (optional, for DELETE requests).**
8. **Stop the capture in the HTTP Sniffer.**
9. **Search for the `GET /api/behaviors/entities` request in the HTTP Sniffer.**
10. **Copy the value of the `Cookie` header and paste it into your config file.**
11. **Copy the value of the `x-amzn-alexa-app` header and paste it into your config file.**
12. **Copy the CSRF value found at the end of the cookie and paste it into your config file.**
13. **For device deletion:**
    - Look for a `DELETE` request containing `/api/phoenix/appliance/`.
    - Copy the part after `api/phoenix/appliance/` but before `%3D%3D_` and set it as the device identifier.
14. **Update the host to match the host your Alexa App is making requests to (e.g., `eu-api-alexa.amazon.co.uk`).**

If you get an error, try updating the HOST, USER_AGENT, CSRF, or COOKIE values from the latest captured requests. See the Troubleshooting section below for more details.

## Usage

You can run the CLI tool directly (no need to use `-m` or specify the module path) thanks to the `project.scripts` configuration in `pyproject.toml`:
```sh
uv run alexa_manager --help
```

### CLI Arguments

| Argument                | Description                                                                                   |
|------------------------|-----------------------------------------------------------------------------------------------|
| `--delete-entities`    | Delete Alexa skill entities that match the configured filter.                                  |
| `--delete-endpoints`   | Delete Alexa GraphQL endpoints (devices/endpoints discovered via GraphQL).                     |
| `--delete-groups`      | Delete all Alexa groups.                                                                      |
| `--create-groups`      | Create Alexa groups for each Home Assistant area.                                             |
| `--get-entities`       | Output Alexa skill entities as a table.                                                       |
| `--get-endpoints`      | Output Alexa GraphQL endpoints as a table.                                                    |
| `--get-groups`         | Output Alexa groups as a table.                                                               |
| `--get-ha-areas`       | Output Home Assistant areas as a table.                                                       |
| `--get-ha-mapping`     | Output mapping of HA entity IDs to Alexa Application IDs for each area.                       |
| `--alexa-only`         | Run in Alexa Only mode (skip all Home Assistant dependent steps).                             |
| `--dry-run`           | Simulate all destructive actions. Only GET requests are performed; DELETE, PUT, POST actions are displayed (using Rich) and not executed. Useful for previewing what would happen without making changes. |
| `--interactive`        | Enable interactive mode for batch actions, requiring user confirmation.                        |
| `--help`               | Show help message and exit.                                                                   |

**Examples:**
```sh
uv run alexa_manager --get-entities
uv run alexa_manager --delete-entities --delete-groups
uv run alexa_manager --create-groups
uv run alexa_manager --get-ha-areas
uv run alexa_manager --alexa-only
uv run alexa_manager --delete-entities --dry-run
uv run alexa_manager --create-groups --dry-run
python main.py --get-ha-mapping
python main.py --interactive --delete-entities
```

**Alexa Only Mode:**
You can run the tool in Alexa Only mode to skip all Home Assistant dependent steps (such as retrieving HA areas or mapping HA entities):
```sh
uv run alexa_manager --alexa-only
```
When --alexa-only is specified, any Home Assistant-dependent actions (including --create-groups) will be skipped and have no effect. Home Assistant configuration entries are not required and will not cause errors in this mode. This mode is useful if you only want to manage Alexa entities and groups without any Home Assistant integration.

**Dry Run Mode:**
You can use the tool with `--dry-run` to preview all actions without making any changes:
```sh
uv run alexa_manager --delete-entities --dry-run
uv run alexa_manager --create-groups --dry-run
```
- Only GET requests are performed.
- DELETE, PUT, POST actions are displayed using Rich and not executed.
- If a step depends on the result of a destructive action, the result is mocked for workflow continuity.
- Output is verbose and clearly indicates simulated actions.

**Interactive Mode:**
Interactive mode can be enabled with `--interactive` for actions that modify or delete entities, groups, or endpoints. In this mode, the script will prompt for confirmation before proceeding with each action. This provides an additional safety net to prevent accidental changes.

To use interactive mode:
```sh
uv run alexa_manager --delete-entities --interactive
uv run alexa_manager --create-groups --interactive
```
In interactive mode, you will be asked to confirm each action by typing `yes` or `no`. Review the proposed changes carefully before confirming.

## Testing

- All tests are in the `tests/` directory.
- To run the test suite (from the project root):
  ```sh
  uv run -m pytest -v
  ```
- Tests use `pytest` and follow PEP 257 docstring conventions.

## Coding Standards

- Follows [PEP 8](https://peps.python.org/pep-0008/) and [PEP 257](https://peps.python.org/pep-0257/) for code and docstrings.
- Uses [Ruff](https://github.com/astral-sh/ruff) for linting and style checks.
- All functions and classes are type-annotated using the `typing` module.
- See `pyproject.toml` for dependencies and project metadata.

## Contributing

Contributions are welcome! Please ensure your code is well-documented, tested, and follows the project conventions.

## Troubleshooting

- Try changing the `HOST` address in your config to your local Amazon address, as found in the HTTP Sniffer requests.
- Try changing the `USER_AGENT` value to match the one found in the HTTP Sniffer requests.
- If you encounter CSRF errors, update the `CSRF` value from the latest DELETE request.
- If you have used the script previously, update the `COOKIE` value from the latest GET or DELETE request.

## Acknowledgements

> "An Amazon employee told me 'have fun with that' when I asked him how to delete devices connected to an Alexa skill. So I did." — Pytonballoon810

Special thanks to:
- [Pytonballoon810](https://github.com/Pytonballoon810) for the original inspiration and script.
- [HennieLP](https://github.com/hennielp) for help with the original script and README, and HTTP sniffing.

## Disclaimer

This script is not officially supported by Amazon and may break at any time. Use at your own risk. See LICENSE for details.

---

For more details, see the comments in the source code and configuration files.
