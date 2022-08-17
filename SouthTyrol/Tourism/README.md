# Introduction

This project analyses the spatial distribution of tourism establishments in the province of South Tyrol, Italy, locally
known as Südtirol or Alto Adige.

# Example
See the jupyter notebook [here](notebooks/Tourism%20in%20South%20Tyrol.ipynb).

# Visualisations

See this [Tableau workbook](https://public.tableau.com/app/profile/lucas.chizzali/viz/TourisminSouthTyrol/Heatmap?publish=yes)
or the more extensive Streamlit app below.

# Set-up

## 1 Get the code & set environmental variables

The below instructions are for Linux or MacOS.

```commandline
git clone https://github.com/calyptis/DataJournalism.git
cd DataJournalism/Tourism/SouthTyrol
source prepare_env.sh
```

## 2. Obtain the data

```commandline
python src/api_calls.py
```

## 3. Prepare the data

```commandline
python src/prepare_data.py
```

## 4. Run the dashboard

```commandline
streamlit run src/app.py
```

# Datasources
- Shapefiles are obtained from the [Geocatalogue of South Tyrol](http://geokatalog.buergernetz.bz.it/geokatalog/#!). 
  Specifically, the two files used in this project are:
    - `BEVÖLKERUNG UND WIRTSCHAFT` -> `Gesellschaft` -> `Ämtliche Bevölkerung`
    - `GRUNDLAGEN UND PLANUNG` -> `Grenzen` -> `Gemeinden`
    - An additional useful source is [https://www.catastobz.it/index_de.html](https://www.catastobz.it/index_de.html)
- Tourism data is obtained from the [Opendatahub API](https://tourism.opendatahub.bz.it/swagger/index.html#/Accommodation/SingleAccommodationRoom)
