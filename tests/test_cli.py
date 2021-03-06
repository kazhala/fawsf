from botocore.exceptions import ClientError
from fzfaws.utils.exceptions import InvalidFileType
import os
from fzfaws.utils.fileloader import FileLoader
import unittest
from unittest.mock import patch
from fzfaws.cli import main, copy_config
import sys
import io
from pathlib import Path
import tempfile


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.capturedOuput = io.StringIO()
        sys.stdout = self.capturedOuput
        config_path = Path(__file__).resolve().parent.joinpath("../fzfaws/fzfaws.yml")
        fileloader = FileLoader()
        fileloader.load_config_file(config_path=str(config_path))

    def tearDown(self):
        sys.stdout = sys.__stdout__

    @patch("fzfaws.cli.s3")
    @patch("fzfaws.cli.ec2")
    @patch("fzfaws.cli.cloudformation")
    def test_subparser(self, mocked_cloudformation, mocked_ec2, mocked_s3):
        sys.argv = [__file__, "cloudformation", "-h"]
        main()
        mocked_cloudformation.assert_called_once_with(["-h"])

        sys.argv = [__file__, "ec2", "ssh", "-A"]
        main()
        mocked_ec2.assert_called_once_with(["ssh", "-A"])

        mocked_ec2.reset_mock()
        sys.argv = [__file__, "ec2", "start"]
        main()
        mocked_ec2.assert_called_once_with(["start", "--wait"])

        sys.argv = [__file__, "s3", "download"]
        main()
        mocked_s3.assert_called_once_with(["download", "--hidden"])

    @patch("fzfaws.cli.copy_config")
    def test_parser(self, mocked_copy):
        sys.argv = [__file__, "-h"]
        self.assertRaises(SystemExit, main)
        self.assertRegex(
            self.capturedOuput.getvalue(), r"usage: fzfaws .*",
        )

        sys.argv = [__file__, "--copy-config"]
        self.assertRaises(SystemExit, main)
        mocked_copy.assert_called_once()

        self.capturedOuput.truncate(0)
        self.capturedOuput.seek(0)
        sys.argv = [__file__]
        self.assertRaises(SystemExit, main)
        self.assertRegex(self.capturedOuput.getvalue(), r"^usage: fzfaws \[-h\].*")

    def test_copy_config(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            os.environ["XDG_CONFIG_HOME"] = tmpdirname
            copy_config()
            if not Path("%s/fzfaws/fzfaws.yml" % tmpdirname).is_file():
                self.fail("config file not properly copied")

    @patch("fzfaws.cli.get_default_args")
    def test_exceptions(self, mocked_args):
        mocked_args.side_effect = InvalidFileType
        sys.argv = [__file__, "s3"]
        self.assertRaises(SystemExit, main)
        self.assertEqual(
            self.capturedOuput.getvalue(), "Selected file is not a valid file type\n"
        )

        mocked_args.side_effect = SystemExit
        sys.argv = [__file__, "s3"]
        self.assertRaises(SystemExit, main)

        mocked_args.side_effect = KeyboardInterrupt
        sys.argv = [__file__, "s3"]
        self.assertRaises(SystemExit, main)

        mocked_args.side_effect = ClientError
        sys.argv = [__file__, "s3"]
        self.assertRaises(SystemExit, main)
