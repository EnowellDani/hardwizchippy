# HardWizChippy

Your ad-free CPU, GPU and SoC specifications database by KBitWare.

## Overview

HardWizChippy is a cross-platform Flutter application that provides comprehensive CPU specifications and benchmarks. Features include:

- 📱 Cross-platform support (iOS, Android, Web, Windows, macOS, Linux)
- 🔍 Advanced search and filtering
- ❤️ Favorites management
- 🌙 Dark/Light theme support
- 📊 Detailed CPU specifications and benchmarks
- 🏷️ Manufacturer-based organization (Intel, AMD)

## Getting Started

### Prerequisites

- Flutter SDK 3.10.7 or higher
- Dart SDK

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/EnowellDani/hardwizchippy.git
   ```

2. Install dependencies:
   ```bash
   flutter pub get
   ```

3. Run the app:
   ```bash
   flutter run
   ```

## Project Structure

```
hardwizchippy/
├── lib/                    # Flutter application source
│   ├── core/              # Shared utilities, constants, theme
│   ├── models/            # Data models
│   ├── providers/         # State management (Provider)
│   ├── screens/           # Application screens
│   ├── services/          # API and data services
│   └── widgets/           # Reusable UI components
├── assets/                # Static assets (JSON data, images)
├── scraper/              # Python web scraper for CPU data
├── database/             # SQL schema files
└── test/                 # Unit and widget tests
```

See [lib/README.md](lib/README.md) for detailed architecture documentation.

## Data Sources

The app uses a local JSON database of CPU specifications. The `scraper/` directory contains Python tools for collecting and updating this data.

## License

Copyright © 2024 KBitWare. All rights reserved.
