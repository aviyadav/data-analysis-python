# Analyzing Data with NumPy

This project demonstrates the use of the `numpy` library to handle and manipulate structured data from a CSV file. It focuses on loading data, accessing specific subsets, and transforming the data layout using transposition.

## 🚀 Features

- **CSV Data Loading**: Uses `numpy.genfromtxt` to efficiently load textual data from a CSV file into a NumPy array.
- **Data Slicing**: Demonstrates how to access the first few records of a dataset.
- **Array Transposition**: Showcases the `transpose()` method to flip the axes of the array, converting rows to columns and vice versa.

## 📁 Project Structure

```text
analyzing-data-with-numpy/
├── pyproject.toml              # Project configuration and dependencies
├── name_age_sex_data.csv       # Dataset containing Name, Sex, and Age
└── src/
    └── analyzing_data_with_numpy/
        ├── __init__.py         # Package initialization
        └── main.py             # Core logic for data analysis
```

## 🛠️ Prerequisites

- [uv](https://docs.astral.sh/uv/) (Fast Python package and project manager)
- Python >= 3.14

## ⚙️ Getting Started

### Installation
Initialize the project environment and install dependencies:
```sh
uv sync
```

### Running the Analysis
Execute the main script using the defined console script:
```sh
uv run main
```

### Building the Project
To package the project into a distributable format (wheel/sdist):
```sh
uv build
```

## 📊 Data Details

The project uses `name_age_sex_data.csv`, which contains the following columns:
- **Name**: The name of the individual.
- **Sex**: Gender (Male/Female).
- **Age**: Age of the individual.

The data is loaded as a NumPy array with a Unicode string type (`U7`) to accommodate the textual nature of the dataset.
