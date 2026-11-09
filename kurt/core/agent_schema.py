"""Provider-native JSON schemas for the complete executable agent toolset."""
import re


def agent_function_schemas(tools):
    from kurt.capabilities.bridge import function_schemas
    native={tool['function']['name']:tool for tool in function_schemas()}
    output=[]
    for tool in tools:
        if tool['name'] in native:
            output.append(native[tool['name']]);continue
        properties,required={},[]
        for name,description in tool['parameters'].items():
            lower=description.lower()
            optional=lower.startswith('optional') or 'default' in lower
            if not optional:required.append(name)
            if 'list of objects' in lower:
                fields={'old_str':{'type':'string'},'new_str':{'type':'string'}} if name=='edits' else {'role':{'type':'string'},'task':{'type':'string'}}
                schema={'type':'array','items':{'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}}
            elif name in ('argv','args','steps','verification') and ('list' in lower or 'array' in lower):
                schema={'type':'array','items':{'type':'string'}}
            elif 'boolean' in lower: schema={'type':'boolean'}
            elif re.search(r'\bint(?:eger)?\b',lower): schema={'type':'integer'}
            elif lower.startswith('object'): schema={'type':'object','additionalProperties':True}
            else: schema={'type':'string'}
            properties[name]={**schema,'description':description}
        output.append({'type':'function','function':{'name':tool['name'],'description':tool['description'],
                        'parameters':{'type':'object','properties':properties,'required':required,'additionalProperties':False}}})
    return output
