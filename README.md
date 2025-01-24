# doc-ci/gha-publish

A GitHub Action that takes previously downloaded artifacts and pushes them into a target Git repository.
This action is the last step in the validate/build/publish workflow and thus depends on other actions from this repository.
It also needs a private SSH key that can be used to deploy to the target Git repository.

This Action will perform destructive steps on the target Git repository:

* If there are more than 35 commits in your target repository, it will take the current repository state, remove all commits and force-push to the original branch.
* It will delete all top-level directories from the target repository that are not listed in the `relevant-dirs` input.

Minimal example job:

```yaml
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v2
        with:
          path: artifact-dir
      - uses: openSUSE/doc-ci@gha-publish
        env:
          DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
        with:
          artifact-path: artifact-dir
```


## Inputs

Name | Required? | Type | Default | Explanation
-----|-----------|------|---------|------------
`DEPLOY_KEY` | yes | environment variable, string | "" | SSH private key for push access to repository.
`artifact-path` | yes | string | "" | Local path to the artifacts that were previously downloaded
`publish-repo` | no | string | "default" | SSH path to target repository. `git@github.com` can be shortened to `gh`. By default, this is generated based on the name of the source directory that this action is running in.
`publish-branch` | no | string | "gh-pages" | Branch of target repository to push to.
`relevant-dirs` | no | string | "" | Top-level directories in the target repository that must not be deleted, space-separated (e.g. `relevant-dir-1 relevant-dir-2`). If the parameter is empty, will not perform any deletions.
`repo-reset-after` | no | string | 35 | Number of commits after which to clean up the target repository with a force push. `0` disables the repo reset.

## Outputs

Name | Type | Explanation
-----|------|------------
`exit-publish` | int | An exit code
