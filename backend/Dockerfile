FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy

WORKDIR /app

# Step 1: Install lightweight core packages and database drivers
RUN pip install --no-cache-dir \
    fastapi>=0.100.0 \
    uvicorn[standard]>=0.22.0 \
    pydantic[email]>=2.0 \
    pydantic-settings>=2.0.0 \
    python-dotenv>=1.0.0 \
    asyncpg>=0.28.0 \
    sqlalchemy[asyncio]>=2.0.0 \
    redis>=4.6.0 \
    "elasticsearch<9.0.0" \
    celery>=5.3.1 \
    python-multipart>=0.0.6 \
    passlib[bcrypt]>=1.7.4 \
    python-jose[cryptography]>=3.3.0 \
    cryptography>=41.0.0 \
    beautifulsoup4>=4.12.0 \
    requests>=2.31.0 \
    aiohttp>=3.8.0 \
    pyotp>=2.9.0

# Step 2: Install numpy and pandas (separated to limit peak memory usage)
RUN pip install --no-cache-dir numpy>=1.24.0 pandas>=2.0.0

# Step 3: Install scipy and scikit-learn (very heavy compiling, isolated to prevent OOM crashes)
RUN pip install --no-cache-dir scipy>=1.10.0 scikit-learn>=1.3.0

# Step 4: Install NLP and crawling packages
RUN pip install --no-cache-dir spacy>=3.6.0 scrapy>=2.9.0 playwright>=1.35.0

# Step 5: Pre-download spaCy English language model
RUN python -m spacy download en_core_web_sm

COPY . .

EXPOSE 8000
