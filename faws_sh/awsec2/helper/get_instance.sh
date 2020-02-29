# display all instance through fzf and return the selected instance data
# @params
# $1 ${region} optional
function get_instance() {
  # if there is flag, meaning a region other than default is selected
  # request region specific ec2 or using default region
  if [[ -z "$1" ]]
  then
    local selected_instance=$(aws ec2 describe-instances \
        --query 'Reservations[].Instances[].[InstanceId,State.Name,InstanceType,Tags[?Key==`Name`]|[0].Value,KeyName,PublicDnsName]' \
        --output text | sed 's/\'$'\t/ | /g' | fzf --exit-0 | sed 's/\'$'\s//g' | awk -F '|' '{print $1 " " $2 " " $5 " " $6}')
  else
    local selected_instance=$(aws ec2 describe-instances --region "$selected_region" \
        --query 'Reservations[].Instances[].[InstanceId,State.Name,InstanceType,Tags[?Key==`Name`]|[0].Value,KeyName,PublicDnsName]' \
        --output text | sed 's/\'$'\t/ | /g' | fzf --exit-0 | sed 's/\'$'\s//g' | awk -F '|' '{print $1 " " $2 " " $5 " " $6}')
  fi 
  echo "$selected_instance"
}