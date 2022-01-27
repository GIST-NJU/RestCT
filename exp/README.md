# Replication of Experiments

The performance of RestCT is evaluated under 11 real-world subject APIs of two servcie systems, *GitLab* and *Bing Maps* (their Swagger specifications are available in the `spec` directory). This document provides instructions for replicating the above experiments.

For the instructions that use Docker images to replicate the experiments, please see [README_DOCKER](../README_DOCKER.md).



## Test GitLab (6 APIs)

### 1. Service Deployment

We rely on Docker to deploy and test *GitLab* in a local environemnt. First, run the following command to deploy the service:

```bash
# pull the image
docker pull gitlab/gitlab-ce:13.10.3-ce.0
# run the service
docker run --detach \
    --hostname gitlab.example.com \
    --publish 30001:443 --publish 30000:80 --publish 30002:22 \
    --name gitlab \
    --restart always \
    --volume /srv/gitlab/config:/etc/gitlab \
    --volume /srv/gitlab/logs:/var/log/gitlab \
    --volume /srv/gitlab/data:/var/opt/gitlab \
    --env GITLAB_ROOT_PASSWORD=password1 \
    gitlab/gitlab-ce:13.10.3-ce.0
```



### 2. Authentication Configuration

Note that the authentication is required for *GitLab*, and we need to configure it. We use an **OAuth2 token** to authenticate with the API by passing it in the `Authorization` header.

Now, we have an administrator account. Next, we request an `access_token` by sending an HTTP request:

```bash
curl -d 'grant_type=password&username=admin@example.com&password=password1' -X POST http://localhost:30000/oauth/token
```

The response received should like:

```bash
{
 "access_token": "de6780bc506a0446309bd9362820ba8aed28aa506c71eedbe1c5c4f9dd350e54",
 "token_type": "bearer",
 "expires_in": 7200,
 "refresh_token": "8257e65c97202ed1726cf9571600918f3bffb2544b26e00a61df9897668c33a1",
 "created_at": 1607635748
}
```

As such, we can then use the **OAuth2 token** in the header:

```bash
curl --header "Authorization: Bearer OAUTH-TOKEN" "http://localhost:30000/api/v4/projects"
```


### 3. Run the Experiments 
**Suppose the abs path of RESTCT is `/root/RestCT`**, run the following command to generate experiment scripts:

```bash
python /root/RestCT/exp/scripts.py --gitlabAuth <OAUTH-TOKEN>
```
* Replace `<OAUTH-TOKEN>` with token got above


For RQ1, we run the following command to automated test each API
```bash
cd /root/RestCT/exp/output/GitLab_RQ1
nohup bash /root/RestCT/exp/runScripts/GitLab_RQ1/runAll.sh 2>&1 &
```

For RQ2, we run the following command to automated test each API
```bash
cd /root/RestCT/exp/output/GitLab_RQ2
nohup bash /root/RestCT/exp/runScripts/GitLab_RQ2/runAll.sh 2>&1 &
```

The experiment is not over until the word "Done!" appears in the standard output `./nohup.out`

**The RestCT tool requests the same GitLab server, so the two groups of experiments must not be parallel**

**For RQ1, we commended to use subject `branch`, `commit`,`groups`, or `repository` as a quick assessemnt (about 2~6 minutes for each to execute), because the other two subjects might take about 30 minutes to execute**. 
For example, run the following command to test subject `branch`:
```bash
bash /root/RestCT/exp/runScripts/GitLab_RQ1/scripts/Branch_2_3_2.sh 2>&1
```
The experiment will end in a few minutes

Once the test execution finishes, several evaluation metrics will be calculated and recorded. See the end of this document for the interpretation of these results.



## Test BingMaps (5 APIs)

We rely on the publicly hosted service of Bing Maps to perform testing, so there is no need to deploy the service.



## 1. Authentication Configuration

Authentication is also required for *Bing Maps*. To do this, please register an account at [Bing Maps Dev Center](https://www.bingmapsportal.com/) at first.

Then, apply an API key according to the following steps:

- Sign in to the Bing Maps Dev Center with your Microsoft Account.
- Go to “My Account” and click on “My Keys.”
- Fill out the form and click “Create” and get your API key details.



### 2. Run the Experiments 

**Suppose the abs path of RESTCT is `/root/RestCT`**, run the following command to generate experiment scripts:

```bash
python /root/RestCT/exp/scripts.py --bingMapAuth <KEY-TOKEN>
```

* Replace `<KEY-TOKEN>` with your API key 

For RQ1, we run the following command to automated test each API
```bash
cd /root/RestCT/exp/output/BingMap_RQ1
nohup bash /root/RestCT/exp/runScripts/BingMap_RQ1/runAll.sh 2>&1 &
```

For RQ2, we run the following command to automated test each API
```bash
cd /root/RestCT/exp/output/BingMap_RQ2
nohup bash /root/RestCT/exp/runScripts/BingMap_RQ2/runAll.sh 2>&1 &
```

The experiment is not over until the word "Done!" appears in the standard output `./nohup.out`

**Do not run the two groups of experiments in parallel, avoiding affecting the experimental results**



## Experimental Data

When the execution of RestCT finishes, the test results can be found in the `xxx` direcotry. These include:

* `statistics.csv`: this file records primary metrics for evaluation (tht is, the numbers reported in the paper), including:
  * coverage strengths applied (*SStrength*=2, *EStrength*=3, and *AStrength*=2, by default)
  * the number of operation sequences generated (*Seq*)
  * average length of each operation sequence (*Len*)
  * 1-way and 2-way sequences that are actually tested (*C_1_way* and *C_2_way*)
  * number of all t-way sequences of operations (*All C_SStrength_way*)
  * number of bugs detected (*Bug*)
  * execution time costs, in seconds (*Cost*) 
* `swagger`
  * `acts`: this directory records input and output files of the ACTS covering array generator
  * `bug`: this directory records the detailed information of bugs detected
  * `log`: this directory records the stdout obtained during the tool execution
  * `unresolvedParams.json`: this file records the set of unsolved parameters during the tool execution
