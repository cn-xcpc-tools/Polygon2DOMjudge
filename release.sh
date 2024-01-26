#! /bin/bash -e

VERSION="${1}"
if [ -z "${VERSION}" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

poetry version "${VERSION}"

git add .
git commit -m "chore: release v${VERSION}"
git tag v"${VERSION}"
git push --tags

echo "Release v${VERSION} created."
