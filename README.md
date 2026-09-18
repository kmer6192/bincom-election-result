# Bincom Election Results Application

A Flask web application created for the Bincom Python Developer preliminary interview test.

The application uses the provided 2011 Delta State election database.

## Features

### 1. Individual polling unit results

Users can select a polling unit and display the scores recorded for each political party.

### 2. Summed LGA results

Users can select a Local Government Area and display the summed results of all polling units belonging to that LGA.

The calculation uses the `polling_unit` and `announced_pu_results` tables. It does not use the `announced_lga_results` table.

### 3. New polling unit results

Users can:

- select a Local Government Area;
- select one of its wards;
- create a new polling unit;
- enter scores for all political parties;
- save the polling unit and its results in MySQL.

The ward selection is dynamically updated according to the selected LGA.

## Technologies

- Python 3
- Flask
- MySQL 8
- HTML
- CSS
- JavaScript
- Docker and Docker Compose

## Project structure

```text
bincom-election-result/
├── database/
│   └── bincom_test.sql
├── static/
│   └── style.css
├── templates/
│   ├── index.html
│   ├── lga_results.html
│   └── new_polling_unit.html
├── .env.example
├── .gitignore
├── app.py
├── docker-compose.yml
├── README.md
└── requirements.txt
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/kmer6192/bincom-election-result.git
cd bincom-election-result
```

### 2. Create the environment file

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Update the passwords inside `.env` if necessary.

### 3. Start MySQL

Make sure Docker Desktop is running, then execute:

```bash
docker compose up -d
```

The SQL file is imported automatically when the MySQL volume is created for the first time.

Check the container:

```bash
docker ps --filter "name=bincom_mysql"
```

### 4. Create a Python virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 5. Install the dependencies

```bash
python -m pip install -r requirements.txt
```

### 6. Run the application

```bash
python app.py
```

Open the application at:

```text
http://127.0.0.1:5000
```

## Application pages

| Page | URL |
|---|---|
| Individual polling unit results | `http://127.0.0.1:5000/` |
| Summed LGA results | `http://127.0.0.1:5000/lga-results` |
| Enter new polling unit results | `http://127.0.0.1:5000/new-polling-unit` |

## Database configuration

The application reads the following variables from `.env`:

```env
MYSQL_ROOT_PASSWORD=
MYSQL_DATABASE=
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_PORT=
```

The `.env` file is ignored by Git to prevent database passwords from being published.

## Author

Brunel Nangoum-Tchatchoua
