# GoutHelper

Web app and API for all things gout.

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

License: MIT

## Overview

Suite of tools and informational pages to help clinicians manage and patients understand gout. The methodology is based on guidelines, empiric evidence, and rheumatology tribal knowledge. The site is written in Python using the Django framework. Some JQuery is used for the front end. The site is deployed on Digital Ocean using Docker.

## Features

- Treatment Aids: Decision tools that take some information and tell you how to
  treat gout.
- Decision Aids: Decision tools that take some information and tell you
  whether you should treat gout and other useful stuff.
- Informational Pages: Pages that explain gout and its treatment in plain English.

## Work-In-Progress

- Content: Most of the content for the site is written in Markdown. Anyone with a knowledge of gout or rheumatology who would like to contribute, please get in touch.
  The guide for writing Markdown for GoutHelper is in EDITORS.md.
- Continuous Integration and Deployment: After much novice trial-and-error, CI/CD is working via GitHub actions, making life slightly easier. An outstanding issue is that templates are cached and do not update when I update a Markdown file. I have to update the file, log in to the admin, and open the model instance referencing the .md file and save it in order for the template to refresh. Anyone who has advice on how to refresh the cache or specific model instances programmatically during CI/CD please reach out.

# To Do / Timeline

- Gout is complicated enough that a fair amount of user input is required in order to get quality recommendations (i.e. lots of form fields). The "rest" branch is my initial attempts to **build out the API** using Django REST framework such that I will be able to take data in non-form formats that could be more easily consolidated from other sources.
- Once the API is functional, my goal is to attempt using AI tools to translate medical records into discrete Python datatypes or a data format compatible with the API (i.e. JSON with correct key-value pairing). This could make getting recommendations from GoutHelper a lot easier.
- I also want to build out GoutHelper's tools to manage gout longitudinally, i.e. monitor labs and in the context of flares, potential side effects, and changes in medical status.
