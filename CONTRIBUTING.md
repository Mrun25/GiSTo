# Contributing to GiSTo

First off, thank you for considering contributing to GiSTo! It's people like you that make GiSTo such a great tool.

## Where do I go from here?

If you've noticed a bug or have a feature request, make sure to check our [Issues](../../issues) to see if someone else in the community has already created a ticket. If not, go ahead and make one!

## Fork & create a branch

If this is something you think you can fix, then fork GiSTo and create a branch with a descriptive name.

A good branch name would be (where issue #325 is the ticket you're working on):

```sh
git checkout -b 325-add-new-feature
```

## Get the test suite running

Make sure to install all the required dependencies. You can run the smoke tests for the backend via:

```sh
cd backend
python tests/smoke_test.py
```

## Implement your fix or feature

At this point, you're ready to make your changes. Feel free to ask for help if you need it.

## Make a Pull Request

At this point, you should switch back to your master branch and make sure it's up to date with GiSTo's master branch:

```sh
git remote add upstream https://github.com/your-username/gisto.git
git checkout master
git pull upstream master
```

Then update your feature branch from your local copy of master, and push it!

```sh
git checkout 325-add-new-feature
git rebase master
git push --set-upstream origin 325-add-new-feature
```

Finally, go to GitHub and make a Pull Request.

## Code Style

- Python (Backend & Bot): We follow PEP 8. Please run `flake8` or `black` before submitting your pull request.
- JavaScript/React (Dashboard): We follow standard React guidelines and use ESLint.
