#!/bin/bash
# Publish collected artifacts in a Git repo that can then be served via GH Pages.

RED='\e[31m'
GREEN='\e[32m'
BLUE='\e[34m'
BOLD='\e[1m'
RESET='\e[0m'

log() {
  # $1 - optional: string: "+" for green color, "-" for red color
  # $2 - message
  colorcode="$BLUE"
  [[ "$1" == '+' ]] && colorcode="$GREEN" && shift
  [[ "$1" == '-' ]] && colorcode="$RED" && shift
  echo -e "$colorcode${1}$RESET"
}

fail() {
  # $1 - message
  echo -e "$RED$BOLD${1}$RESET"
  exit 1
}

succeed() {
  # $1 - message
  echo -e "$GREEN$BOLD${1}$RESET"
  exit 0
}

gha_fold() {
  name="$1"
  prefix='::group::'
  if [[ $1 == '--' ]]; then
    name=''
    prefix='::endgroup::'
  fi
  echo -e "$prefix$name"
}

# including `tree` into our container would probably also be an option
create_basic_index() {
  # $1 - location
  # $2 - dir levels to include

  oview_selfname=$(echo -e "$1" | grep -oP '[^/]+/?$' | tr -d '/')
  oview_dirs=$(cd "$1" || return; ls -d -- */ | sed -r 's,/$,,' | sort -u)
  [[ "$2" == 2 ]] && oview_dirs=$(cd "$1" || return; ls -d -- */*/ | sed -r 's,/$,,' | sort -u)

  {
    echo "<!DOCTYPE html><head><meta charset='utf-8'><title>Index of $oview_selfname</title></head>"
    echo "<body><h1>$oview_selfname</h1><ul>"
    for d in $oview_dirs; do
      echo "<li><a href='$d/'>$d</a></li>"
    done
    echo "</ul></body>"
  } > "$1/index.html"
}


# shellcheck disable=SC2027,SC2046
echo "Running "$(basename "$0")", "$(sha1sum "$0" | cut -b1-8)" [ verify locally with: sha1sum "$(basename "$0")" | cut -b1-8 ]."

gha_fold "Environment"
  for var in GITHUB_JOB GITHUB_EVENT_NAME \
      GITHUB_ACTOR GITHUB_REPOSITORY_OWNER GITHUB_REPOSITORY GITHUB_REF GITHUB_SHA \
      HOME RUNNER_TEMP RUNNER_WORKSPACE \
      GITHUB_ACTION_REPOSITORY GITHUB_ACTION_REF; do
    echo "$var=\"${!var:-EMPTY-}\""
  done
gha_fold --

commit="$GITHUB_SHA"
repo=$(echo "$GITHUB_REPOSITORY" | grep -oP '[^/]+$')
publish_branch_dir=$(echo "$GITHUB_REF" | sed -r -e 's#^refs/heads/##' -e 's#^main(t(enance)?)?/##')
relevantbranches=''
# Repo to publish in
publish_repo="gh:SUSEdoc/$repo.git"
# Branch to publish in
branch='gh-pages'
# Maximum number of commits to allow on target repo's target branch before
# flattening history into a single commit that is then force-pushed (avoids
# large repos)
maxcommits=35
# How often to retry pushing to the target repo if the initial push fails
# (this can happen due to concurrent CI runs that have pushed before and created
# a different state)
push_attempts=3

artifact_dir='artifact-dir'

exitcode=0

while [[ $1 ]]; do
  case $1 in
    artifact-path=*)
      artifact_dir=$(echo "$1" | cut -f2- -d'=')
      shift
      ;;
    publish-repo=*)
      [[ $(echo "$1" | cut -f2- -d'=') = 'default' ]] || publish_repo=$(echo "$1" | cut -f2- -d'=')
      shift
      ;;
    publish-branch=*)
      [[ $(echo "$1" | cut -f2- -d'=') = '' ]] || branch=$(echo "$1" | cut -f2- -d'=')
      shift
      ;;
    relevant-dirs=*)
      relevantbranches=$(echo "$1" | cut -f2- -d'=')
      shift
      ;;
    repo-reset-after=*)
      [[ $(echo "$1" | cut -f2- -d'=' | grep -oP '^[0-9]+$') ]] && maxcommits=$(echo "$1" | cut -f2- -d'=')
      shift
      ;;
    --)
      shift
      break
      ;;
    *)
      log - "Command-line argument \"$1\" cannot be parsed."
      shift
      ;;
  esac
done

[[ -z "$DEPLOY_KEY" ]] && fail "The DEPLOY_KEY environment variable is unset. To clone/push the target repo, this script need an SSH private key as a deploy key."


gha_fold "Setting up SSH"
  # /root/ is not the same as $HOME, and ssh -vvv indicates we need to use /root/
  ssh_dir="/root/.ssh"
  ssh_socket="/tmp/ssh-$RANDOM.sock"
  mkdir "$ssh_dir"

  key_file="$ssh_dir/id_rsa_deploy"
  echo -e "$DEPLOY_KEY" > "$key_file"
  # SSH refuses to use the key if it's world-readable
  chmod 0600 "$key_file"
  # Start the SSH authentication agent
  ssh-agent -s -a "$ssh_socket"
  export SSH_AUTH_SOCK="$ssh_socket"
  # Display the key fingerprint from the file
  ssh-keygen -lf "$key_file"
  # Import the private key
  ssh-add "$key_file"
  # Display fingerprints of available SSH keys
  ssh-add -l
  # Accept foreign SSH key
  ssh-keyscan github.com 2>/dev/null >> "$ssh_dir/known_hosts"
  # Make sure we're always using the new SSH key for github.com repos
  echo -e "\nHost gh\n  Hostname github.com\n  User git\n  IdentityFile $key_file" \
    >> "$ssh_dir/config"

  # The custom_ssh command is useful for debugging SSH connectivity. If
  # you're so inclined, you can add e.g. `-vvv` (but that make reading the log
  # of `git clone` rather unpleasant, even a simple `-v` nets 60+ lines).
  custom_ssh="$HOME/ssh-verbose"
  echo 'ssh -v $@' > "$custom_ssh"
  chmod +x "$custom_ssh"
  export GIT_SSH="$custom_ssh"

gha_fold --


while [[ $push_attempts -gt 0 ]]; do

gha_fold "Cloning target repository and performing maintenance"

  # Set the git username and email used for the commits
  git config --global user.name "SUSE Docs Bot"
  git config --global user.email "doc-team+docbot@suse.com"

  log "Cloning target repository $publish_repo\n"
  pubrepo="$PWD/$repo"
  git clone \
    --no-tags --no-recurse-submodules \
    "$publish_repo" "$pubrepo" \
    || fail "target repository could not be cloned."

  git="git -C $pubrepo"

  $git checkout "$branch" || $git checkout -b "$branch"

  # Every 35 commits ($maxcommits), we reset the repo, so it does not become too
  # large. (When the repo becomes too large, that increases the probability of
  # CI failing because of a timeout while cloning.)
  # shellcheck disable=SC2209
  if [[ "$maxcommits" -gt 0 && $(PAGER=cat $git log --oneline --format='%h' | wc -l) -ge "$maxcommits" ]]; then
    log "Resetting target repository, so it does not become too large"
    # nicked from: https://stackoverflow.com/questions/13716658
    $git checkout --orphan new-branch
    $git add -A . >/dev/null
    $git commit -am "Automatic repo reset via CI"
    $git branch -D "$branch"
    $git branch -m "$branch"
    $git push -f origin "$branch" || fail "Target repository could not be force-pushed to."
  elif [[ "$maxcommits" -gt 0 ]]; then
    log "Not resetting target repository, as there are fewer than $maxcommits commits in the target repository."
  else
    log "Not resetting target repository, because 'repo-reset-after=0' is set."
  fi


  # Clean up build results of branches that we don't build anymore

  if [[ -n "$relevantbranches" ]]; then
    # The currently published branches == first-level dirs except hidden dirs
    pubdirs=$(cd "$pubrepo" || exit 1; ls -d -- */ | sed -r 's,/$,,' | sort -u)

    # dir name = branch name, but with replacement '/' => ','
    #  [Doing this replacement opens us up to corner cases where two different
    #   branches "share" (i.e. fight over) a directory but this seems better than
    #   either creating and having to deal with nested directory structures or
    #   having to do URL-safe encoding of stuff.]
    relevantbranchdirs=$(echo -e "$relevantbranches" | tr ' ' '\n' | tr '/' ',' | sort -u)

    oldpubdirs=$(comm -2 -3 <(echo -e "$pubdirs") <(echo -e "$relevantbranchdirs"))

    for olddir in $oldpubdirs; do
      log "Removing repository content for \"$olddir\" because it is now irrelevant."
      rm -r "${pubrepo:?}/$olddir"
    done
  else
    log "Not removing old directories as parameter 'relevant-dirs' is unset."
  fi

  # Out with the old content from the branch we want to build...
  mypubdir=$(echo "$publish_branch_dir" | tr '/' ',')
  log "Removing repository content for \"$mypubdir\", will replace the content in the next step."
  rm -r "${pubrepo:?}/$mypubdir"

gha_fold --


# In with the new content...
# Copy the HTML and single HTML files for each DC file
gha_fold "Copying built files to target repository"

  mkdir -p "${pubrepo:?}/$mypubdir"
  for dir in "$artifact_dir"/*; do
    log "Copying contents of $dir to $mypubdir"
    cp -r "$dir"/* "${pubrepo:?}/$mypubdir/"
  done

  # Publish file names with an underscore:
  # https://help.github.com/en/enterprise/2.14/user/articles/files-that-start-with-an-underscore-are-missing
  touch "$pubrepo/.nojekyll"

gha_fold --

gha_fold "Adding index.html pages for top-level dirs."

  create_basic_index "$pubrepo" 1
  for dir in "$pubrepo"/*; do
    log "Adding index.html for $dir"
    [[ -d "$dir" ]] && create_basic_index "$dir" 2
  done

gha_fold --


# Add all changed files to the staging area, commit and push
gha_fold "Pushing build results generated from commit $commit (from $repo)"

  $git add -A .
  log "Commit"
  $git commit -m "Automatic rebuild after $repo commit $commit"
  log "Push"
  $git push origin "$branch"
  pushcode="$?"

gha_fold --

  if [[ "$pushcode" -eq 0 ]]; then
    break
  fi
  push_attempts=$((push_attempts - 1))
  [[ "$push_attempts" -eq 0 ]] && fail "Target repository could not be pushed to repeatedly. Giving up."
  log - "Target repository could not be pushed to. Retrying."
  rm -rf "$pubrepo"

done

# FIXME: The exit code is kinda not generated in a useful way at all
echo "exit-publish=$exitcode" >> $GITHUB_OUTPUT
if [[ "$exitcode" -gt 0 ]]; then
  fail "Publishing build results failed."
else
  succeed "Publishing build results succeeded."
fi
