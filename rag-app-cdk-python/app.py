#!/usr/bin/env python3
import os

import aws_cdk as cdk

from rag_app_cdk_python.stack import RagAppCdkPythonStack


app = cdk.App()
RagAppCdkPythonStack(app, "RagAppCdkPythonStack")
app.synth()
