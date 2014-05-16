_yak() {
  local cur prev opts services
  COMPREPLY=()
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  opts="start stop restart info interrupt console log err out details test"
  services="$(yak !)"
  
  case "${prev}" in
      start|stop|restart|info|interrupt|console|log|err|out|details)
          COMPREPLY=( $(compgen -W "${services}" -- ${cur}) )
          return 0
          ;;
      *)
          ;;
  esac
  
  COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
  return 0
}

complete -F _yak yak
