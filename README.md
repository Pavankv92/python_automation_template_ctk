# Python Robotics Automation Template

A comprehensive template for building robotics automation dashboards using Python and CustomTkinter. This project provides a clean, scalable starting point for GUI applications that connect to and control robotic instruments, featuring validated input widgets, real-time communication, and a layered MVC-style architecture.

![Robotics Dashboard](media/robot_app.png)

## Features

- **CustomTkinter GUI** — modern, themeable dashboard interface (light/dark mode)
- **Layered architecture** — strict separation between models, views, controllers, and pages
- **Validated input widgets** — custom CTk widgets with per-keystroke and focus-out validation
- **Field registry** — define form fields once as dataclasses; variables, persistence, and validation are automatic
- **Controller layer** — hardware logic is fully decoupled from the UI and unit-testable without a display
- **Settings persistence** — per-page JSON settings files loaded and saved automatically
- **Thread-safe messaging** — ticket queue pattern for safe communication between background threads and the UI
- **Type safety** — full mypy support with comprehensive type annotations
- **Testing ready** — pytest configuration included

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd python_automation_template_ctk
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   # or with Poetry:
   poetry install
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

## Project structure

```
python_automation_template_ctk/
│
├── constants.py                   # FieldTypes enum — zero project imports
│
├── models/
│   ├── base.py                    # SettingsModel — JSON persistence
│   └── fields.py                  # FieldDef, FieldRegistry — pure Python, no tk/ctk
│
├── views/
│   ├── widgets.py                 # Validated CTk widgets + FIELD_WIDGET_MAP
│   ├── base_page.py               # BasePage — inherit for every tab
│   └── dialogs.py                 # Reusable modal dialogs (ErrorDialog, ConfirmDialog)
│
├── controllers/
│   ├── base_controller.py         # BaseController — connection state machine
│   └── instrument_controller.py   # Concrete robot controller (hardware logic only)
│
├── pages/
│   └── instrument_page.py         # Robot tab — UI only, delegates to controller
│
├── utils/                         # TicketHandler, Ticket, TicketPurpose, SerialInterface
├── application.py                 # Root window — registers pages in PAGES list
└── app.py                         # Entry point
```

## Architecture

The project follows a strict layered architecture. Dependencies only flow downward — no layer imports from a layer above it.

```
constants.py                 ← zero project imports
      ↓
models/fields.py             ← imports constants only
      ↓
views/widgets.py             ← imports constants, models
views/dialogs.py             ← imports customtkinter only
views/base_page.py           ← imports models, views, utils
      ↓
controllers/base_controller  ← imports utils only (never imports tk/ctk)
controllers/*_controller     ← imports base_controller
      ↓
pages/*_page.py              ← imports base_page, controller, dialogs
      ↓
application.py               ← imports page classes only
```

### Layer responsibilities

| Layer | File(s) | Owns | Never touches |
|---|---|---|---|
| Constants | `constants.py` | `FieldTypes` enum | everything else |
| Models | `models/fields.py` | `FieldDef`, `FieldRegistry` | tk, ctk, hardware |
| Widgets | `views/widgets.py` | CTk widget classes, `FIELD_WIDGET_MAP` | hardware, settings |
| Base page | `views/base_page.py` | var creation, settings I/O, queue, validation | hardware, page layout |
| Dialogs | `views/dialogs.py` | reusable modal dialogs | business logic |
| Controller | `controllers/` | connection state, hardware calls, ticket posting | tk, ctk widgets |
| Page | `pages/` | UI layout, wiring actions to controller | hardware, settings logic |
| Application | `application.py` | tab registration | page internals |

### Field registry pattern

Fields are defined once as dataclasses. Everything else — the tk variable type, settings persistence, widget selection, and validation — is derived automatically.

```python
# pages/instrument_page.py
@dataclass
class InstrumentFields(FieldRegistry):
    ip_address: FieldDef = field(default_factory=lambda: FieldDef(
        key="ip_address",
        label="Robot IP address",
        field_type=FT.string,
        default="198.168.0.1",
        required=True,
    ))
```

`FieldDef` properties derived automatically:

| Property | Source |
|---|---|
| tk variable type (`StringVar`, `IntVar`, …) | `field_type` |
| Storage type (`"str"`, `"int"`, …) | `field_type` |
| Widget class (`RequiredEntry`, `ValidatedSpinbox`, …) | `FIELD_WIDGET_MAP[field_type]` |
| Settings dict format | `fd.as_settings_dict()` |
| LabelInput `field_spec` | `fd.as_field_spec()` |

### Controller pattern

Controllers own all hardware logic and communicate back to the UI exclusively via tickets — they never call `configure()` on a widget. This makes them fully testable without a display.

```python
# controllers/instrument_controller.py
class InstrumentController(BaseController):
    def _validate_params(self, params):
        # pure logic — returns {key: error}, no UI
        ...

    def _do_connect(self, params):
        # hardware SDK calls only
        self._post_progress(f"Connecting to {params['ip_address']}…")
        # self._connection = RobotSDK.connect(params["ip_address"])

    def _do_disconnect(self):
        # self._connection.close()
        ...
```

The page calls `self._controller.connect(self.get_values())` and reacts to the state change — it has no idea how the connection works.

### Thread-safe messaging

Background threads never touch the UI directly. They post `Ticket` objects to the page's queue; the `<<CheckQueue>>` virtual event drains the queue safely on the main thread.

```python
# In a background thread (via controller):
self._post_status("Calibrating…")
self._post_progress("Step 2 of 5")
self._post_completed("Done")

# BasePage drains the queue automatically — no extra code needed in pages
```

## Adding a new page

Adding an instrument page requires touching exactly four files, each with a single clear concern:

### 1. Define your fields — `models/fields.py` pattern

```python
from dataclasses import dataclass, field
from ..models.fields import FieldDef, FieldRegistry
from ..constants import FieldTypes as FT

@dataclass
class CalibrationFields(FieldRegistry):
    target_distance: FieldDef = field(default_factory=lambda: FieldDef(
        key="target_distance",
        label="Target distance (mm)",
        field_type=FT.decimal,
        default=100.0,
        min=0.0,
        max=1000.0,
        increment=0.5,
    ))
    iterations: FieldDef = field(default_factory=lambda: FieldDef(
        key="iterations",
        label="Iterations",
        field_type=FT.integer,
        default=5,
        min=1,
        max=100,
    ))
```

### 2. Create a controller — `controllers/calibration_controller.py`

```python
from .base_controller import BaseController

class CalibrationController(BaseController):
    def _validate_params(self, params):
        errors = {}
        if params.get("target_distance", 0) <= 0:
            errors["target_distance"] = "Must be greater than 0"
        return errors

    def _do_connect(self, params):
        # replace with real SDK call
        self._post_progress("Connecting to calibration hardware…")

    def _do_disconnect(self):
        pass

    def _do_execute(self, params):
        self._post_progress("Calibrating…")
        # run calibration routine
        self._post_completed("Calibration complete")
```

### 3. Create the page — `pages/calibration_page.py`

```python
from dataclasses import dataclass, field
from ..views.base_page import BasePage
from ..views import widgets as w
from ..controllers.calibration_controller import CalibrationController
from .fields import CalibrationFields   # defined above

class CalibrationPage(BasePage):
    SETTINGS_FILE = "calibration.json"

    def __init__(self, *args, **kwargs):
        self._registry = CalibrationFields()
        super().__init__(*args, **kwargs)
        self._controller = CalibrationController(self._message_queue)

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        frame = w.LabelFrame(self, label_text="Calibration")
        frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)

        for i, fd in enumerate(self._registry.all()):
            w.LabelInput(
                frame.content,
                label_text=fd.label,
                var=self._vars[fd.key],
                field_spec=fd.as_field_spec(),
            ).grid(row=i, column=0, sticky="ew", padx=8, pady=4)
```

### 4. Register in the application — `application.py`

```python
from .pages.calibration_page import CalibrationPage

class Application(ctk.CTk):
    PAGES = [
        ("Robot",       InstrumentMainPage),
        ("Calibration", CalibrationPage),   # ← one line
    ]
```

That is everything. Settings persistence, variable wiring, queue handling, and validation are all inherited from `BasePage` automatically.

## Widgets reference

| Widget | Field type | Notes |
|---|---|---|
| `RequiredEntry` | `FT.string` | Non-empty validation on focus-out |
| `DateEntry` | `FT.iso_date_string` | YYYY-MM-DD format enforced per keystroke |
| `ValidatedCombobox` | `FT.string_list` | Autocomplete, validates against `values` list |
| `ValidatedRadioGroup` | `FT.short_string_list` | Horizontal radio buttons |
| `ValidatedSpinbox` | `FT.decimal` / `FT.integer` | `+`/`-` buttons, range clamping, type-aware |
| `BoundText` | `FT.long_string` | Multi-line, bound to a `tk.StringVar` |
| `CTkCheckBox` | `FT.boolean` | Standard CTk checkbox |

All validated widgets expose `error: tk.StringVar` and `trigger_focusout_validation() → bool`, making them compatible with `BasePage._get_errors()` automatically.

## Contributing

Contributions are welcome. Please open an issue before submitting a pull request for significant changes.

## License

See `LICENSE` for details.