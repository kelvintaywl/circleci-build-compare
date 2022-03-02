# CircleCI Build Compare

Compare (diff) between builds on CircleCI Cloud to see what changed!

Also, this dogfoods CircleCI features whenever applicable :nerd_face:

## Pipeline

**How to use?**

1. Trigger the CircleCI pipeline on the `main` branch.
2. Enter the 2 builds' links as pipeline parameters `build-link-a` and `build-link-b`.
3. Note that the 2 build links **must** be about a specific **job**, not the workflow.

![How to Trigger the Pipeline](trigger-pipeline.png)

> Check out the _.circleci/config.yml_ for more details.
### Workflows


`diff-builds`

This does the following:

1. Run a sanity check on the 2 build links (e.g., same project)
2. Parse build link to retrieve build information via CircleCI API (`parallelism: 2`)
    * save build information as artifact (YML file).
3. Generate a visual diff on the build information.

```mermaid
flowchart LR
    support((Support Team)) -- trigger pipeline --> validate[validate: sanity check]
    subgraph ide1 [CircleCI]
    validate --> infoA[info 0: parse build info for A]
    validate --> infoB[info 1: parse build info for B]
    infoA -- store_artifact --> artifact[(Artifacts)]
    infoB -- store_artifact --> artifact
    infoA -- attach_workspace --> visualize[visualize: visual diff]
    infoB -- attach_workspace --> visualize
    end
```
