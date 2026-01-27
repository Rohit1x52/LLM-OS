from typing import Dict, List, Set
from enum import Enum


class ActionCategory(Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SEND = "send"
    RECEIVE = "receive"
    SEARCH = "search"
    ANALYZE = "analyze"
    SCHEDULE = "schedule"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    EXECUTE = "execute"
    COMPILE = "compile"
    TRANSFORM = "transform"
    NOTIFY = "notify"


class ActionTaxonomy:
    def __init__(self):
        self.action_verbs: Dict[ActionCategory, Set[str]] = {
            ActionCategory.CREATE: {
                "create", "make", "build", "generate", "compose", "write",
                "draft", "construct", "design", "produce", "develop"
            },
            ActionCategory.READ: {
                "read", "view", "show", "display", "open", "check",
                "review", "examine", "inspect", "browse", "look"
            },
            ActionCategory.UPDATE: {
                "update", "modify", "change", "edit", "revise", "alter",
                "adjust", "amend", "correct", "refine", "improve"
            },
            ActionCategory.DELETE: {
                "delete", "remove", "erase", "clear", "purge", "destroy",
                "eliminate", "discard", "drop", "clean"
            },
            ActionCategory.SEND: {
                "send", "email", "forward", "share", "transmit", "deliver",
                "dispatch", "post", "publish", "submit", "upload"
            },
            ActionCategory.RECEIVE: {
                "receive", "get", "fetch", "retrieve", "collect", "obtain",
                "acquire", "download", "pull", "gather"
            },
            ActionCategory.SEARCH: {
                "search", "find", "locate", "lookup", "query", "seek",
                "explore", "discover", "filter", "sort"
            },
            ActionCategory.ANALYZE: {
                "analyze", "process", "evaluate", "assess", "calculate",
                "compute", "measure", "compare", "summarize", "extract"
            },
            ActionCategory.SCHEDULE: {
                "schedule", "plan", "arrange", "book", "reserve", "set",
                "organize", "calendar", "remind", "notify"
            },
            ActionCategory.DOWNLOAD: {
                "download", "fetch", "pull", "retrieve", "get", "grab"
            },
            ActionCategory.UPLOAD: {
                "upload", "push", "send", "transfer", "move", "copy"
            },
            ActionCategory.EXECUTE: {
                "execute", "run", "launch", "start", "perform", "do",
                "carry out", "implement", "apply", "trigger"
            },
            ActionCategory.COMPILE: {
                "compile", "build", "assemble", "package", "bundle"
            },
            ActionCategory.TRANSFORM: {
                "transform", "convert", "translate", "encode", "decode",
                "format", "reshape", "restructure"
            },
            ActionCategory.NOTIFY: {
                "notify", "alert", "remind", "inform", "message", "ping"
            }
        }
        
        self.verb_to_category = {}
        for category, verbs in self.action_verbs.items():
            for verb in verbs:
                self.verb_to_category[verb.lower()] = category
    
    def get_category(self, verb: str) -> ActionCategory:
        return self.verb_to_category.get(verb.lower())
    
    def get_verbs_for_category(self, category: ActionCategory) -> Set[str]:
        return self.action_verbs.get(category, set())
    
    def is_valid_action(self, verb: str) -> bool:
        return verb.lower() in self.verb_to_category
    
    def get_all_action_verbs(self) -> List[str]:
        all_verbs = []
        for verbs in self.action_verbs.values():
            all_verbs.extend(verbs)
        return sorted(all_verbs)