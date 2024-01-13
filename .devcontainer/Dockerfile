FROM mcr.microsoft.com/devcontainers/base:1-bookworm

ARG USERNAME=vscode

# https://github.com/conda-forge/miniforge
RUN curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh" && \
    bash Mambaforge-$(uname)-$(uname -m).sh -b -p /opt/conda && \
    rm Mambaforge-$(uname)-$(uname -m).sh
    
USER $USERNAME

RUN /opt/conda/bin/mamba init && \
    echo "mamba activate base" >> /home/$USERNAME/.bashrc
