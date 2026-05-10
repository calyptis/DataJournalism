FROM python:3.11-slim

# System libraries required by geopandas / geoviews (GDAL, GEOS, PROJ)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev gdal-bin \
    libgeos-dev libproj-dev \
    libspatialindex-dev \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

EXPOSE 8080

ENV POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN pip install poetry

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

COPY south_tyrol_tourism/ ./south_tyrol_tourism/
COPY data/dashboard_data/ ./data/dashboard_data/

RUN poetry install --without dev --only-root

ENTRYPOINT ["poetry", "run", "streamlit", "run", "south_tyrol_tourism/app.py", "--server.port=8080"]
