# ORDL Command Post - Python 3.11 Sandbox Image
# Hardened container for secure Python code execution

FROM python:3.11-slim-bookworm

# Security: Create non-root user
RUN groupadd -r ordlrunner -g 1000 && \
    useradd -r -g ordlrunner -u 1000 -s /sbin/nologin -d /tmp ordlrunner

# Install system dependencies with minimal footprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /tmp

# Install common ML/data science packages
# These are pre-installed for performance (avoid downloading on each run)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
    numpy>=1.24.0 \
    pandas>=2.0.0 \
    scikit-learn>=1.3.0 \
    matplotlib>=3.7.0 \
    seaborn>=0.12.0 \
    scipy>=1.11.0 \
    requests>=2.31.0 \
    pillow>=10.0.0 \
    beautifulsoup4>=4.12.0 \
    lxml>=4.9.0 \
    html5lib>=1.1 \
    sympy>=1.12 \
    statsmodels>=0.14.0

# Security: Set restrictive permissions
RUN chmod 755 /tmp && \
    chown ordlrunner:ordlrunner /tmp

# Switch to non-root user
USER ordlrunner

# Security: Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp

# Default command (overridden at runtime)
CMD ["python", "--version"]

# Labels
LABEL org.ordl.component="sandbox" \
      org.ordl.language="python" \
      org.ordl.version="3.11" \
      org.ordl.security.level="hardened"
