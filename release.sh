#! /bin/bash

CUR_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"

VERSION="${1}"
if [ -z "${VERSION}" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

poetry version "${VERSION}"

pushd "${CUR_DIR}/.." || exit 1

git add .
git commit -m "chore: release v${VERSION}"
git tag v"${VERSION}"
git push --tags

echo "Release v${VERSION} created."

popd || exit 1
