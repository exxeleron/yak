_yak() {
  local cur prev opts services
  COMPREPLY=()
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  opts="start stop kill restart info interrupt console log err out details"
  services="$(yak !)"
  negservices="$(yak ! | sed -e 's/^/!/g')"

  case "${prev}" in
      yak)
          COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
          return 0
          ;;
      *)
          COMPREPLY=( $(compgen -W "${services} ${negservices}" -- ${cur}) )
          return 0
          ;;
  esac
}

complete -F _yak yak
