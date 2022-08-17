# Base image to use
FROM continuumio/miniconda3

# Expose port 8080
EXPOSE 8080

# Copy needed files into Docker image
COPY requirements.txt app/requirements.txt
COPY ./src /src
COPY ./data/dashboard_data /data/dashboard_data

# Install all requirements (plus adding plots directory)
# Adding conda clean --all to remove unnecessary files
# NOTE: Chain RUN commands to reduce the size of the resulting Docker image
RUN conda config --append channels conda-forge && \
    conda install --file app/requirements.txt && \
    conda clean --all && \
    mkdir /plots

# Set the working directory
WORKDIR src/

# Run the application on port 8080
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080"]
