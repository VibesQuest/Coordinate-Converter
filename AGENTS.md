<source_control_tools>
This repository uses **jj (Jujutsu)** for version control.

## Rules

* Do **not** use `git` commands.
* Do **not** stage files (`git add` is not used).
* Avoid interactive commands (`-i` flags).
* Always record changes with `jj`.

## Basic commands

Check repository state:

jj status
jj diff
jj log

## Workflow

Create commits frequently (snapshot your work):

jj commit -m "<conventional commit>"

During iterative work, update the previous commit:

jj squash

Start a new logical change after finishing a commit:

jj new

## Update main

jj bookmark set main -r @-
jj git push --remote origin --bookmark main

## Move tag

jj tag set v0.1.0 -r main --allow-move

*If the tag already exists on the remote, force-push the tag update.*

## Commit messages

Use **Conventional Commits**:

feat(scope): description
fix(scope): description
refactor(scope): description
docs: description
test: description
chore: description

## Recovery

If the repository ends up in a bad state:

jj op log
jj op restore <operation-id>
</source_control_tools>