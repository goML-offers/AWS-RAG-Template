# THIS FILE CONSISTS OF DIFFERENT TARGETS FOR BUILDING, TESTING, AND DEPLOYING A PROJECT.
# MODIFY/ADD THE TARGETS AS PER YOUR PROJECT REQUIREMENTS.


.DEFAULT_GOAL = help

# Include environment settings
-include .env

SRC_DIR := src
TEST_DIR := tests
DIRS_TO_LINT := $(SRC_DIR) $(TEST_DIR)

#\ Use the Python executable in PATH
PYTHON3 ?= python3
# PYTHON3 ?= ${PYTHON311}
USE_VENV ?= .venv\Scripts\python.exe
SERVER_PORT ?= 8000
LOCAL_PORT ?= 8000

# Github Secrets
AWS_REGION ?= $(AWS_REGION)
AWS_ACCOUNT_ID?= $(AWS_ACCOUNT_ID)
ECR_REPOSITORY ?= $(ECR_REPOSITORY)
IMAGE_TAG?=latest



# Common ECR image repository
ECR_REGISTRY ?= $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com


.PHONY: init
init: ## initialize local dev environment (runs `install` too)
	@if not exist .env copy .env.example .env


venv:  ## create Python venv
	${PYTHON3} -m venv .venv
	${USE_VENV} -m pip install --upgrade pip


.PHONY: install
install: venv ## install all required packages (will also create venv)
	${USE_VENV} -m pip install -r requirements.txt

.PHONY: run
run: venv ## create a local docker image, and run the docker image
	python3 -m src.main

.PHONY: format
format: venv ## format all Python code with black
	${USE_VENV} -m black ${DIRS_TO_LINT}

.PHONY: lint
lint: venv  ## lint all Python code with pylint + validate formatting
	${USE_VENV} -m black ${DIRS_TO_LINT} --check
	${USE_VENV} -m pylint ${DIRS_TO_LINT}


.PHONY: test
test: venv ## run all tests with pytest
	${USE_VENV} -m pytest ${TEST_DIR}


.PHONY: ecr-login
ecr-login:  ## authenticate docker with ECR using AWS credentials
	aws ecr get-login-password --region $(AWS_REGION) \
		| docker login --username AWS --password-stdin "${ECR_REGISTRY}"


.PHONY: build
build:  ## build docker image based on current working copy
	docker build --no-cache -t ${ECR_REPOSITORY} -f Dockerfile .

.PHONY: tag
tag: ## After the build completes, tag your image so you can push the image to this repository:
	docker tag $(ECR_REPOSITORY):latest ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}


.PHONY: push
push: ## Run the following command to push this image to your newly created AWS repository:
	docker push $(ECR_REGISTRY)/$(ECR_REPOSITORY):$(IMAGE_TAG)


.PHONY: deploy_image
deploy_image: ## Deploy the latest image on aws lambda function given name of lambda function
	aws lambda update-function-code \
  --function-name ${AWS_LAMBDA_FUNC} \
  --image-uri ${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}


.PHONY: build-and-push
build-and-push: ecr-login build tag push

.PHONY: deploy
deploy: build-and-push deploy_image


.PHONY: local-build
local-build : ## build the docker image locally using Dockerfile-local
	docker build --no-cache -t ${ECR_REPOSITORY} -f Dockerfile-local .



.PHONY: local-run-docker
local-run-docker: ## run docker the docker image in the terminal
	docker run --env-file=.env --publish ${LOCAL_PORT}:${SERVER_PORT} ${ECR_REPOSITORY}

.PHONY: help
help:  ## Show this help message
	@echo Available targets:
	@findstr /R /C:"^[ a-zA-Z_-]*:.*##" $(MAKEFILE_LIST) | for /F "tokens=1* delims=:" %%A in ('more') do @echo  %%A: %%B
