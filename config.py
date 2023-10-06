#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

""" Bot Configuration """


class DefaultConfig:
    """ Bot Configuration """

    PORT = 8080

    # APP_ID and APP_PASSOWRD to be changed according to the Azure Bot ID and Password
    APP_ID = os.environ.get("MicrosoftAppId", "168f23b3-fe02-4fa1-8357-dd1091d894e5")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "zVp8Q~oPgX2FM25fqH8bWikv2v6~5Ap1IJuBmc1~")

    # Put OpenAI key here
    openai_api_key = ''

    # Based URL to be changed according to the hosted server's url
    base_url = "https://sutd-bot-server.azurewebsites.net/"

