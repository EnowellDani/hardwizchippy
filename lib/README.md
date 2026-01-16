# HardWizChippy - Flutter App

## Project Structure

```
lib/
├── main.dart                    # Application entry point
├── core/                        # Core utilities and shared code
│   ├── core.dart               # Core module barrel file
│   ├── constants/              # Application constants
│   │   ├── constants.dart      # Constants barrel file
│   │   ├── api_constants.dart  # API configuration constants
│   │   └── app_constants.dart  # General app constants
│   └── theme/                  # Theme configuration
│       ├── theme.dart          # Theme barrel file
│       ├── app_colors.dart     # Color palette definitions
│       └── app_theme.dart      # ThemeData configurations
├── models/                     # Data models
│   ├── models.dart            # Models barrel file
│   └── cpu.dart               # CPU model and related classes
├── providers/                  # State management (Provider)
│   ├── providers.dart         # Providers barrel file
│   ├── cpu_provider.dart      # CPU data state management
│   └── theme_provider.dart    # Theme state management
├── screens/                    # Application screens/pages
│   ├── screens.dart           # Screens barrel file
│   ├── home_screen.dart       # Main navigation screen
│   ├── cpu_list_screen.dart   # CPU listing with search/filter
│   ├── cpu_detail_screen.dart # Individual CPU details
│   ├── favorites_screen.dart  # User's favorite CPUs
│   └── settings_screen.dart   # App settings
├── services/                   # Business logic and data services
│   ├── services.dart          # Services barrel file
│   ├── api_service.dart       # Remote API communication
│   └── local_data_service.dart # Local JSON data loading
└── widgets/                    # Reusable UI components
    ├── widgets.dart           # Widgets barrel file
    ├── cpu_card.dart          # CPU display card
    ├── filter_bottom_sheet.dart # Filter options UI
    ├── search_bar_widget.dart  # Search input widget
    └── shimmer_loading.dart    # Loading placeholders
```

## Architecture Overview

This project follows a clean, organized structure with:

- **Barrel Files**: Each module has an `index.dart` or `module.dart` file that exports all public APIs
- **Core Module**: Shared constants, theme configuration, and utilities
- **Provider Pattern**: State management using the Provider package
- **Service Layer**: Abstracted data access (API and local)
- **Modular Screens**: Each screen is self-contained with its own state

## Import Conventions

Use barrel file imports for cleaner code:

```dart
// Instead of multiple imports:
import '../models/cpu.dart';
import '../models/other_model.dart';

// Use:
import '../models/models.dart';
```

## Getting Started

1. Run `flutter pub get` to install dependencies
2. Run `flutter run` to start the app
