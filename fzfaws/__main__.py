""" Main entry point of the program.

Typical usage example:
    faws <command> --options
"""
import sys
import subprocess
from botocore.exceptions import ClientError
from fzfaws.utils.exceptions import NoCommandFound, NoNameEntered, NoSelectionMade, InvalidFileType, InvalidS3PathPattern
from fzfaws.cform.main import cform
from fzfaws.ec2.main import ec2
from fzfaws.s3.main import s3


def main():
    """Entry function of the fzf.aws module"""

    try:
        if len(sys.argv) < 2:
            raise NoCommandFound()
        available_routes = ['cform', 'ec2', 'keypair', 's3']
        action_command = sys.argv[1]
        if action_command not in available_routes:
            raise NoCommandFound()
        if action_command == 'cform':
            cform(sys.argv[2:])
        elif action_command == 'ec2':
            ec2(sys.argv[2:])
        elif action_command == 's3':
            s3(sys.argv[2:])

    # display help message
    # did'n use argparse at the entry level thus creating similar help message
    except NoCommandFound as e:
        print('usage: faws [-h] {cform, ec2, keypair, s3} ...\n')
        print('A better aws cli experience with the help of fzf\n')
        print('positional arguments:')
        print('  {cform,ec2,keypair,s3}\n')
        print('optional arguments:')
        print('  -h, --help            show this help message and exit')
    except NoNameEntered:
        print('No name was entered for the operation')
        print('Current operation require a name input, please re-run the operation')
        print('Exiting..')
    except InvalidFileType:
        print('Selected file is not a valid template file type')
        print('Exiting..')
    except InvalidS3PathPattern:
        print(
            'Invalid s3 path pattern, valid pattern(Bucket/ or Bucket/path/to/upload)')
        print('Exiting..')
    except KeyboardInterrupt:
        print('\nExit')
    except subprocess.SubprocessError:
        print('No selection was made')
        print('Exit..')
    except (ClientError, Exception) as e:
        print(e)


if __name__ == '__main__':
    main()
