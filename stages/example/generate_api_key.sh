OPTIND=1 # Reset in case getopts has been used previously in the shell.
username=""

while getopts ":u:p:" opt; do
  case ${opt} in
  u) username=$OPTARG ;;
  \?) echo "Usage: $0 [-u]" ;;
  esac
done

shift $((OPTIND - 1))

[ "${1:-}" = "--" ] && shift

docker compose exec alert python -m alert.create_api_key --username $1
