# Base image to use
FROM continuumio/miniconda3

# Expose port 8080
EXPOSE 8080

# Copy requirements.txt file into app directory
COPY requirements.txt app/requirements.txt

# Install all requirements
RUN apt-get update && \
    apt-get install gcc -y && \
    apt-get clean
RUN conda config --append channels conda-forge
RUN conda install --file app/requirements.txt

# Copy needed files into app directory
COPY ./src /src
COPY ./data/dashboard_data /data/dashboard_data
RUN mkdir /plots

# Set working directory
WORKDIR src/

# Run the application on port 8080
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080"]
