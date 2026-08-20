"""Not real Python code — this file exists solely so setuptools treats
``skills/`` as a package, which makes its ``package-data`` glob (see
pyproject.toml) actually bundle the skill tree (SKILL.md files, references/,
etc.) into the built wheel/sdist. Without this, ``skills/`` is an invisible
bare data directory to setuptools and ships in neither — the exact bug that
made a fresh ``pip install jacky-cli`` crash with "Unknown skill(s):
jacky-doctrine" on first launch, since the persona skill physically wasn't
in the installed package at all.
"""
