FROM public.ecr.aws/lambda/python:3.11

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Required to make SQLlite3 work for Chroma.
RUN pip install pysqlite3-binary

# Install the specified packages
RUN pip install -r requirements.txt --upgrade

# For local testing.
EXPOSE 8000

# Set IS_USING_IMAGE_RUNTIME Environment Variable
ENV IS_USING_IMAGE_RUNTIME=True

# Copy all files in ./app and ./db to the Lambda task root
RUN mkdir ${LAMBDA_TASK_ROOT}/app
RUN mkdir ${LAMBDA_TASK_ROOT}/db

COPY app/* ${LAMBDA_TASK_ROOT}/app
COPY db/* ${LAMBDA_TASK_ROOT}/db