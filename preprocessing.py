import logging
from io import StringIO

import nbformat
import tiktoken
from nbformat.reader import NotJSONError


def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """
    Calculates the number of tokens in a string using the specified encoding.

    Args:
        string (str): The input string.
        encoding_name (str): The name of the encoding to use.

    Returns:
        int: The number of tokens in the string.
    """
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(string))


def is_valid_notebook(content):
    """
    Check if the given content is a valid Jupyter notebook.

    Args:
        content (str): The content of the notebook.

    Returns:
        bool: True if the content is a valid notebook, False otherwise.
    """
    try:
        nbformat.reads(content, as_version=4)
        return True
    except NotJSONError:
        return False


def remove_outputs_from_notebook(notebook_content):
    """
    Removes the outputs and execution counts from a Jupyter Notebook.

    Args:
        notebook_content (str): The content of the Jupyter Notebook.

    Returns:
        str: The modified content of the Jupyter Notebook with outputs and execution counts removed.
    """
    if not is_valid_notebook(notebook_content):
        raise ValueError("The content is not a valid Jupyter Notebook")

    notebook = nbformat.reads(notebook_content, as_version=4)

    for cell in notebook.cells:
        if 'outputs' in cell:
            cell['outputs'] = []
        if 'execution_count' in cell:
            cell['execution_count'] = None

    logging.info("Removed outputs from Jupyter Notebook")

    output_stream = StringIO()
    nbformat.write(notebook, output_stream)

    return output_stream.getvalue()
