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
- Continuous Integration and Deployment: To update the site, I currently have to manually log in to the server, Git pull the latest changes, and restart the Docker containers. I would like to automate this process using GitHub Actions but I cannot make the script work properly. If you have experience with GitHub Actions and Docker and want to contribute, please get in touch.
