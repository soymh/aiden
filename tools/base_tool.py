import inspect
import re


class ToolBase:
    """
    Base class for all tools.
    
    Any public method (i.e. not starting with '_') defined in a subclass is treated as a tool.
    The tool's name, description, and JSON schema for its parameters are automatically generated
    by inspecting the method signature and its Sphinx-style docstring.
    """

    def get_tool_spec(self) -> list:
        """
        Returns a list of tool specifications generated from the methods of the class.
        Each tool specification is a dictionary with keys:
          - name: the method name
          - description: the first line of the method's docstring
          - parameters: a JSON schema object generated from the method's parameters
          - function: a reference to the method (to be used when the tool is called)
        """
        tool_specs = []
        for attr_name in dir(self):
            # Skip private methods and attributes
            if attr_name.startswith("_"):
                continue

            attr = getattr(self, attr_name)
            if callable(attr):
                # Ensure the method is defined in the subclass (not inherited)
                if attr.__qualname__.split('.')[0] != self.__class__.__name__:
                    continue

                sig = inspect.signature(attr)
                parameters_schema = {"type": "object", "properties": {}, "required": []}
                # Parse the docstring to extract parameter descriptions
                doc = attr.__doc__ or ""
                param_docs = {}
                for line in doc.splitlines():
                    line = line.strip()
                    if line.startswith(":param"):
                        # Example: ":param equation: The equation to calculate."
                        m = re.match(r":param\s+(\w+):\s*(.*)", line)
                        if m:
                            param_name, description = m.groups()
                            param_docs[param_name] = description

                for name, param in sig.parameters.items():
                    if name == "self":
                        continue
                    # Map type annotations to JSON schema types (default to string)
                    annotation = param.annotation
                    if annotation == int:
                        json_type = "integer"
                    elif annotation == float:
                        json_type = "number"
                    elif annotation == bool:
                        json_type = "boolean"
                    elif annotation == dict:
                        json_type = "object"
                    elif annotation == list:
                        json_type = "array"
                    else:
                        json_type = "string"

                    param_schema = {"type": json_type}
                    if name in param_docs:
                        param_schema["description"] = param_docs[name]
                    parameters_schema["properties"][name] = param_schema
                    if param.default == inspect.Parameter.empty:
                        parameters_schema["required"].append(name)
                if not parameters_schema["required"]:
                    parameters_schema.pop("required")

                # Use the first non-empty line of the docstring as the description
                description = ""
                for line in doc.splitlines():
                    line = line.strip()
                    if line:
                        description = line
                        break

                tool_spec = {
                    "name": attr.__name__,
                    "description": description,
                    "parameters": parameters_schema,
                    "function": attr,
                }
                tool_specs.append(tool_spec)
        return tool_specs
