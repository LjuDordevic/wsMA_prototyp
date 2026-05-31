from pathlib import Path
from core.context.context import ExtParserContext

class ContextBuilder:

    def build(self, parser_result: dict, log: bool) -> ExtParserContext:

        konf = parser_result["kconf"]
        symbol_infos = {}
        symbol_definitions = {}
        symbol_defaults = {}
        symbol_orig_defaults = {}
        configdefault_options = set()
        choice_infos = {}
        choice_definitions = {}
        choice_dep = {}
        unique_syms_nr = len(parser_result["unique_defined_syms"])
        unique_choice_nr = len(parser_result["unique_choices"])
        unique_named_choices_nr = len(parser_result["named_choices"])

        for sym in parser_result["unique_defined_syms"]:
            """ 
            if sym.name == "DEFSTRING" or sym.name=="FOO":
                print(f"sym.name: {sym.name}")
                print(f"sym.origin: {sym.origin}")
                print(f"sym.name_and_loc: {sym.name_and_loc}")
                print(f"\n sym.defaults---------------------")
                for d in sym.defaults:
                    print(f"{d}")
                print(f"\n sym.orig_defaults---------------------")
                for od in sym.orig_defaults:
                    print(f"{od}")
                print(f"\n sym.nodes---------------------")
                for n in sym.nodes:
                    print(f"{n}\n")
                    print(f"{n.dep}\n")
                print(f"\n sym.nodes---------------------")
            """
            if sym.name not in symbol_infos:
                symbol_infos[sym.name] = []
                symbol_definitions[sym.name] = []
                symbol_defaults[sym.name] = []
                symbol_orig_defaults[sym.name] = []

            symbol_infos[sym.name].append(
                {
                    "sym.name": sym.name,
                    "sym.name_and_loc": sym.name_and_loc
                    #'sym.origin' : sym.origin,
                }
            )

            for sd in sym.defaults:
                symbol_defaults[sym.name].append(
                    {
                        "sym.default": sd
                    }
                )

            for sod in sym.orig_defaults:
                symbol_orig_defaults[sym.name].append(
                    {
                        "orig_defaults": sod
                    }
                )

            for node in sym.nodes:

                is_configdefault = getattr(
                    node,
                    "is_configdefault",
                    False
                )

                symbol_definitions[sym.name].append(
                    {
                        "file": getattr(node, "filename", None),
                        "line": getattr(node, "linenr", None),
                        "node": node,
                        "node.defaults": node.defaults,
                        "is_configdefault": is_configdefault
                    }
                )

                if is_configdefault:
                    configdefault_options.add(sym.name)

        for choice in parser_result["unique_choices"]:

            if choice.name not in choice_infos:

                choice_infos[choice.name] = []
                choice_definitions[choice.name] = []
                choice_dep[choice.name] = []

            choice_infos[choice.name].append(
                {
                    "choice.name": choice.name,
                    "choice.syms": choice.syms,
                    #'choice.type' : choice.type,
                    #'choice.name_and_loc' : choice.name_and_loc,
                    #'choice.direct_dep': choice.direct_dep,
                    #'choice.orig_defaults': choice.orig_defaults
                }
            )

            for node in choice.nodes:

                choice_definitions[choice.name].append(
                    {
                        "file": getattr(node, "filename", None),
                        "line": getattr(node, "linenr", None),
                        "node.prompt": node.prompt,
                        "node.defaults": node.defaults,
                        "node.dep": node.dep
                        #'node.item.dd': node.item.direct_dep,
                        #'node.item.name': node.item.name
                    }
                )

                choice_dep[choice.name].append(
                    {
                        "node.defaults": node.defaults,
                        "node.dep": node.dep,
                    }
                )

        context = ExtParserContext(
            symbol_infos = symbol_infos,
            symbol_definitions = symbol_definitions,
            symbol_nr = unique_syms_nr, #len(symbol_definitions),
            configdefault_options = configdefault_options,
            configdefault_options_nr = len(configdefault_options),
            symbol_defaults = symbol_defaults,
            symbol_orig_defaults = symbol_orig_defaults,
            choice_infos = choice_infos,
            choice_definitions = choice_definitions,
            choice_nr = unique_choice_nr, #len(choice_definitions),
            named_choices_nr = unique_named_choices_nr,
            choice_dep = choice_dep,
            parser_result=parser_result,
            srctree=Path(konf.srctree), 
        )

        if log: self._log_parser_context(self.context)
        return context