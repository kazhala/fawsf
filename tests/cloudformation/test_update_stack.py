import os
import io
import sys
import unittest
from unittest.mock import ANY, patch
from fzfaws.cloudformation.update_stack import update_stack
from fzfaws.utils import Pyfzf, FileLoader
from fzfaws.cloudformation import Cloudformation


class TestCloudformationUpdateStack(unittest.TestCase):
    def setUp(self):
        self.capturedOutput = io.StringIO()
        self.data_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../data/cloudformation_template.yaml",
        )
        sys.stdout = self.capturedOutput
        fileloader = FileLoader()
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "../../fzfaws.yml"
        )
        fileloader.load_config_file(config_path=config_path)

    def tearDown(self):
        sys.stdout = sys.__stdout__

    @patch("fzfaws.cloudformation.update_stack.CloudformationArgs")
    @patch("builtins.input")
    @patch("fzfaws.cloudformation.update_stack.Cloudformation")
    def test_non_replacing_update(self, MockedCloudformation, mocked_input, MockedArgs):
        cloudformation = MockedCloudformation()
        cloudformation.stack_name = "testing1"
        cloudformation.stack_details = {
            "Parameters": [
                {"ParameterKey": "SSHLocation", "ParameterValue": "0.0.0.0/0"},
                {"ParameterKey": "Hello", "ParameterValue": "i-0a23663d658dcee1c"},
                {"ParameterKey": "WebServer", "ParameterValue": "No"},
            ],
        }
        cloudformation.set_stack.return_value = None
        cloudformation.execute_with_capabilities.return_value = {}
        mocked_input.return_value = "foo"
        update_stack()
        cloudformation.execute_with_capabilities.assert_called_with(
            Parameters=[
                {"ParameterKey": "SSHLocation", "ParameterValue": "foo"},
                {"ParameterKey": "Hello", "ParameterValue": "foo"},
                {"ParameterKey": "WebServer", "ParameterValue": "foo"},
            ],
            StackName="testing1",
            UsePreviousTemplate=True,
            cloudformation_action=ANY,
        )

        # extra args
        cloudformation.wait.return_value = None
        args = MockedArgs()
        args.set_extra_args.return_value = None
        args.extra_args = {"foo": "boo"}
        update_stack(wait=True, extra=True, profile=True, region="us-east-1")
        MockedCloudformation.assert_called_with(True, "us-east-1")
        cloudformation.wait.assert_called_with(
            "stack_update_complete", "Wating for stack to be updated ..."
        )
        cloudformation.execute_with_capabilities.assert_called_with(
            Parameters=[
                {"ParameterKey": "SSHLocation", "ParameterValue": "foo"},
                {"ParameterKey": "Hello", "ParameterValue": "foo"},
                {"ParameterKey": "WebServer", "ParameterValue": "foo"},
            ],
            StackName="testing1",
            UsePreviousTemplate=True,
            cloudformation_action=ANY,
            foo="boo",
        )
        args.set_extra_args.assert_called_with(
            update=True, search_from_root=False, dryrun=False
        )

    @patch("builtins.input")
    @patch("fzfaws.cloudformation.update_stack.Cloudformation")
    def test_dryrun(self, MockedCloudformation, mocked_input):
        cloudformation = MockedCloudformation()
        cloudformation.stack_name = "testing1"
        cloudformation.stack_details = {
            "Parameters": [
                {"ParameterKey": "SSHLocation", "ParameterValue": "0.0.0.0/0"},
                {"ParameterKey": "Hello", "ParameterValue": "i-0a23663d658dcee1c"},
                {"ParameterKey": "WebServer", "ParameterValue": "No"},
            ],
        }
        cloudformation.set_stack.return_value = None
        cloudformation.execute_with_capabilities.return_value = {}
        mocked_input.return_value = ""
        result = update_stack(dryrun=True)
        self.assertEqual(
            result,
            {
                "Parameters": [
                    {"ParameterKey": "SSHLocation", "UsePreviousValue": True},
                    {"ParameterKey": "Hello", "UsePreviousValue": True},
                    {"ParameterKey": "WebServer", "UsePreviousValue": True},
                ],
                "StackName": "testing1",
                "UsePreviousTemplate": True,
                "cloudformation_action": ANY,
            },
        )

    @patch("fzfaws.cloudformation.update_stack.CloudformationArgs")
    @patch("builtins.input")
    @patch("fzfaws.cloudformation.update_stack.Cloudformation")
    def test_termination(self, MockedCloudformation, mocked_input, MockedArgs):
        cloudformation = MockedCloudformation()
        cloudformation.stack_name = "testing2"
        cloudformation.set_stack.return_value = None
        cloudformation.execute_with_capabilities.return_value = {}
        args = MockedArgs()
        args.set_extra_args.return_value = None
        args.update_termination = True
        update_stack(extra=True)
        cloudformation.client.update_termination_protection.assert_called_with(
            EnableTerminationProtection=True, StackName="testing2"
        )
