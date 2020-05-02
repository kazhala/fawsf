"""contains funtions related to processing a new template"""
from fzfaws.utils.pyfzf import Pyfzf
from fzfaws.utils.util import (
    search_dict_in_list,
    check_dict_value_in_list,
    get_name_tag,
)
from fzfaws.ec2.ec2 import EC2
from fzfaws.route53.route53 import Route53


class ParamProcessor:
    """Process cloudformation template params

    utilizing fzf and boto3 to give better experience of entering params
    for cloudformation

    :param ec2: boto3 client to interact with EC2
    :type ec2: EC2
    :param route53: boto3 client to interact with route53
    :type route53: Route53
    :param params: dictionary of parameter to process
    :type params: dict
    :param original_params: original values of params during update
    :type original_params: dict
    """

    def __init__(self, profile=None, region=None, params=None, original_params=None):
        """constructor of ParamProcessor
        """
        if params == None:
            params = {}
        if original_params == None:
            original_params = {}
        self.ec2 = EC2(profile, region)  # type: EC2
        self.route53 = Route53(profile, region)  # type: Route53
        self.params = params  # type: dict
        self.original_params = original_params  # type: dict
        self.processed_params = []  # type: list
        self._aws_specific_param = [
            "AWS::EC2::AvailabilityZone::Name",
            "AWS::EC2::Instance::Id",
            "AWS::EC2::KeyPair::KeyName",
            "AWS::EC2::SecurityGroup::GroupName",
            "AWS::EC2::SecurityGroup::Id",
            "AWS::EC2::Subnet::Id",
            "AWS::EC2::Volume::Id",
            "AWS::EC2::VPC::Id",
            "AWS::Route53::HostedZone::Id",
        ]  # type: list
        self._aws_specific_list_param = [
            "List<AWS::EC2::AvailabilityZone::Name>",
            "List<AWS::EC2::Instance::Id>",
            "List<AWS::EC2::SecurityGroup::GroupName>",
            "List<AWS::EC2::SecurityGroup::Id>",
            "List<AWS::EC2::Subnet::Id>",
            "List<AWS::EC2::Volume::Id>",
            "List<AWS::EC2::VPC::Id>",
            "List<AWS::Route53::HostedZone::Id>",
        ]  # type: list

    def process_stack_params(self):
        """process the template file parameters
        """

        print("Enter parameters specified in your template below")
        for parameter_key in self.params:
            print(80 * "-")
            default_value = ""  # type: str
            param_header = ""  # type: str

            # print some information
            if "Description" in self.params[parameter_key]:
                param_header += (
                    "Description: %s\n" % self.params[parameter_key]["Description"]
                )
                # print(f"Description: {self.params[parameter_key]['Description']}")
            if "ConstraintDescription" in self.params[parameter_key]:
                param_header += (
                    "ConstraintDescription: %s\n"
                    % self.params[parameter_key]["ConstraintDescription"]
                )
                # print(
                #     f"ConstraintDescription: {self.params[parameter_key]['ConstraintDescription']}"
                # )
            if "AllowedPattern" in self.params[parameter_key]:
                param_header += (
                    "AllowedPattern: %s\n"
                    % self.params[parameter_key]["AllowedPattern"]
                )
                # print(f"AllowedPattern: {self.params[parameter_key]['AllowedPattern']}")
            parameter_type = self.params[parameter_key]["Type"]
            param_header += "Type: %s\n" % parameter_type
            # print(f"Type: {parameter_type}")
            if (
                parameter_type == "List<Number>"
                or parameter_type == "CommaDelimitedList"
            ):
                param_header += "For list type parameters, use comma to sperate items(e.g. values: value1, value2)"
                # print(
                #     "For list type parameters, use comma to sperate items(e.g. values: value1, value2)"
                # )

            if check_dict_value_in_list(
                parameter_key, self.original_params, "ParameterKey"
            ):
                # update with replace current stack flag
                original_value = search_dict_in_list(
                    parameter_key, self.original_params, "ParameterKey"
                )["ParameterValue"]
                parameter_value = self._get_user_input(
                    parameter_key,
                    parameter_type,
                    param_header,
                    "Original",
                    original_value,
                )
            elif "Default" in self.params[parameter_key]:
                # if default value exist
                default_value = self.params[parameter_key]["Default"]
                parameter_value = self._get_user_input(
                    parameter_key,
                    parameter_type,
                    param_header,
                    "Default",
                    default_value,
                )
            else:
                # no default value
                parameter_value = self._get_user_input(
                    parameter_key, parameter_type, param_header
                )

            if type(parameter_value) is list:
                parameter_value = ",".join(parameter_value)
                self.processed_params.append(
                    {"ParameterKey": parameter_key, "ParameterValue": parameter_value}
                )
            else:
                self.processed_params.append(
                    {
                        "ParameterKey": parameter_key,
                        "ParameterValue": str(parameter_value),
                    }
                )

    def _get_user_input(
        self,
        parameter_key,
        parameter_type,
        param_header,
        value_type=None,
        default=None,
    ):
        """get user input

        :param parameter_key: the current parameter key to obtain user input 
        :type parameter_key: str
        :param parameter_type: type of the parameter
        :type parameter_type: str
        :param param_header: information about current parameter
        :type param_header: str
        :param value_type: determine if the current action is update or new creation ('Default|Original')
        :type value_type: str, optional
        :param default: default value of params or orignal value
        :type default: str, optional
        :return: return the user selection through fzf or python input
        :rtype: str
        """

        # execute fzf if allowed_value array exists
        if "AllowedValues" in self.params[parameter_key]:
            param_header += self._print_parameter_key(
                parameter_key, value_type, default
            )
            fzf = Pyfzf()
            for allowed_value in self.params[parameter_key]["AllowedValues"]:
                fzf.append_fzf(allowed_value)
                fzf.append_fzf("\n")
            user_input = fzf.execute_fzf(
                empty_allow=True, print_col=1, header=param_header
            )
        else:
            if parameter_type in self._aws_specific_param:
                param_header += self._print_parameter_key(
                    parameter_key, value_type, default
                )
                user_input = self._get_selected_param_value(parameter_type)
            elif parameter_type in self._aws_specific_list_param:
                param_header += self._print_parameter_key(
                    parameter_key, value_type, default
                )
                user_input = self._get_list_param_value(parameter_type)
            else:
                if not value_type:
                    user_input = input(f"{parameter_key}: ")
                elif value_type == "Default":
                    user_input = input(f"{parameter_key}(Default: {default}): ")
                elif value_type == "Original":
                    user_input = input(f"{parameter_key}(Original: {default}): ")
        if not user_input and default:
            return default
        elif user_input == "''":
            return ""
        elif user_input == '""':
            return ""
        else:
            return user_input

    def _print_parameter_key(self, parameter_key, value_type=None, default=None):
        """helper print function"""
        if value_type:
            return "Choose a value for %s(%s: %s)" % (
                parameter_key,
                value_type,
                default,
            )
            # print(
            #     "Choose a value for %s(%s: %s)" % (parameter_key, value_type, default)
            # )
        else:
            return "Choose a value for %s" % parameter_key
            # print("Choose a value for %s" % parameter_key)

    def _get_selected_param_value(self, type_name):
        """use fzf to display aws specific parameters

        Args:
            type_name: string, name of the parameter
        Returns:
            A string/int of the selected value, require convert to string before
            giving it boto3
        """

        fzf = Pyfzf()
        if type_name == "AWS::EC2::KeyPair::KeyName":
            response = self.ec2.client.describe_key_pairs()
            response_list = response["KeyPairs"]
            fzf.process_list(response_list, "KeyName")
            return fzf.execute_fzf(empty_allow=True)
        elif type_name == "AWS::EC2::SecurityGroup::Id":
            response = self.ec2.client.describe_security_groups()
            response_list = response["SecurityGroups"]
            for sg in response["SecurityGroups"]:
                sg["Name"] = get_name_tag(sg)
            fzf.process_list(response_list, "GroupId", "GroupName", "Name")
            return fzf.execute_fzf(empty_allow=True)
        elif type_name == "AWS::EC2::AvailabilityZone::Name":
            response = self.ec2.client.describe_availability_zones()
            response_list = response["AvailabilityZones"]
            fzf.process_list(response_list, "ZoneName")
            return fzf.execute_fzf(empty_allow=True)
        elif type_name == "AWS::EC2::Instance::Id":
            response = self.ec2.client.describe_instances()
            response_list = []
            for instance in response["Reservations"]:
                response_list.append(
                    {
                        "InstanceId": instance["Instances"][0]["InstanceId"],
                        "Name": get_name_tag(instance["Instances"][0]),
                    }
                )
            fzf.process_list(response_list, "InstanceId", "Name")
            return fzf.execute_fzf(empty_allow=True)
        elif type_name == "AWS::EC2::SecurityGroup::GroupName":
            response = self.ec2.client.describe_security_groups()
            response_list = response["SecurityGroups"]
            for sg in response["SecurityGroups"]:
                sg["Name"] = get_name_tag(sg)
            fzf.process_list(response_list, "GroupName", "Name")
            return fzf.execute_fzf(empty_allow=True)
        elif type_name == "AWS::EC2::Subnet::Id":
            response = self.ec2.client.describe_subnets()
            response_list = response["Subnets"]
            for subnet in response["Subnets"]:
                subnet["Name"] = get_name_tag(subnet)
            fzf.process_list(
                response_list, "SubnetId", "AvailabilityZone", "CidrBlock", "Name"
            )
            return fzf.execute_fzf(empty_allow=True)
        elif type_name == "AWS::EC2::Volume::Id":
            response = self.ec2.client.describe_volumes()
            response_list = response["Volumes"]
            for volume in response["Volumes"]:
                volume["Name"] = get_name_tag(volume)
            fzf.process_list(response_list, "VolumeId", "Name")
            return fzf.execute_fzf(empty_allow=True)
        elif type_name == "AWS::EC2::VPC::Id":
            response = self.ec2.client.describe_vpcs()
            response_list = response["Vpcs"]
            for vpc in response["Vpcs"]:
                vpc["Name"] = get_name_tag(vpc)
            fzf.process_list(response_list, "VpcId", "IsDefault", "CidrBlock", "Name")
            return fzf.execute_fzf(empty_allow=True)
        elif type_name == "AWS::Route53::HostedZone::Id":
            self.route53.set_zone_id()
            return self.route53.zone_id

    def _get_list_param_value(self, type_name):
        """handler if parameter type is a list type

        Args:
            type_name: string, type of the parameter
        Returns:
            processed list of selection from the user
            example:
                ['value', 'value']
        """

        fzf = Pyfzf()
        if type_name == "List<AWS::EC2::AvailabilityZone::Name>":
            response = self.ec2.client.describe_availability_zones()
            response_list = response["AvailabilityZones"]
            fzf.process_list(response_list, "ZoneName")
            return fzf.execute_fzf(multi_select=True, empty_allow=True)
        elif type_name == "List<AWS::EC2::Instance::Id>":
            response = self.ec2.client.describe_instances()
            raw_response_list = response["Reservations"]
            response_list = []
            for item in raw_response_list:
                response_list.append(
                    {
                        "InstanceId": item["Instances"][0]["InstanceId"],
                        "Name": get_name_tag(item["Instances"][0]),
                    }
                )
            fzf.process_list(response_list, "InstanceId", "Name")
            return fzf.execute_fzf(multi_select=True, empty_allow=True)
        elif type_name == "List<AWS::EC2::SecurityGroup::GroupName>":
            response = self.ec2.client.describe_security_groups()
            response_list = response["SecurityGroups"]
            for sg in response_list:
                sg["Name"] = get_name_tag(sg)
            fzf.process_list(response_list, "GroupName")
            return fzf.execute_fzf(multi_select=True, empty_allow=True)
        elif type_name == "List<AWS::EC2::SecurityGroup::Id>":
            response = self.ec2.client.describe_security_groups()
            response_list = response["SecurityGroups"]
            for sg in response_list:
                sg["Name"] = get_name_tag(sg)
            fzf.process_list(response_list, "GroupId", "GroupName", "Name")
            return fzf.execute_fzf(multi_select=True, empty_allow=True)
        elif type_name == "List<AWS::EC2::Subnet::Id>":
            response = self.ec2.client.describe_subnets()
            response_list = response["Subnets"]
            for subnet in response_list:
                subnet["Name"] = get_name_tag(subnet)
            fzf.process_list(
                response_list, "SubnetId", "AvailabilityZone", "CidrBlock", "Name"
            )
            return fzf.execute_fzf(multi_select=True, empty_allow=True)
        elif type_name == "List<AWS::EC2::Volume::Id>":
            response = self.ec2.client.describe_volumes()
            response_list = response["Volumes"]
            for volume in response_list:
                volume["Name"] = get_name_tag(volume)
            fzf.process_list(response_list, "VolumeId", "Name")
            return fzf.execute_fzf(multi_select=True, empty_allow=True)
        elif type_name == "List<AWS::EC2::VPC::Id>":
            response = self.ec2.client.describe_vpcs()
            response_list = response["Vpcs"]
            for vpc in response_list:
                vpc["Name"] = get_name_tag(vpc)
            fzf.process_list(response_list, "VpcId", "IsDefault", "CidrBlock", "Name")
            return fzf.execute_fzf(multi_select=True, empty_allow=True)
        elif type_name == "List<AWS::Route53::HostedZone::Id>":
            self.route53.set_zone_id(multi_select=True)
            return self.route53.zone_ids
