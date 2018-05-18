$PROJECT = $GITHUB_REPO = 'w3g'
$GITHUB_ORG = 'scopatz'

$ACTIVITIES = ['version_bump', 'changelog',
               'tag', 'push_tag', 'pypi',
               'ghrelease']

$VERSION_BUMP_PATTERNS = [
    ('w3g.py', '__version__\s*=.*', "__version__ = '$VERSION'"),
    ('setup.py', 'version\s*=.*', "version='$VERSION',")
    ]
$CHANGELOG_FILENAME = 'CHANGELOG.rst'
$CHANGELOG_TEMPLATE = 'TEMPLATE.rst'
