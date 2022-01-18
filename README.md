# Artifact of "Combinatorial Testing of RESTful APIs"

This artifact includes a testing tool, named **RestCT**, and 11 Swagger specifications created for evaluation. Specifically,

- The RestCT tool implements the testing approach proposed in the paper "Combinatorial Testing of RESTful APIs". This tool takes a Swagger specification file as input, and then adopts combinatorial testing to generates concrete HTTP requests to test RESTful APIs described in the specification.

- The 11 Swagger specifications are created to test APIs of two real-world service systems, GitLab and Bing Maps. The experimantal results reported in the paper are obtained based on these specifications.



## Obtain the Artifact

The artifact is publicly accessible, which can be downloaded from one of the following websites:

* GitHub repository: https://github.com/GIST-NJU/RestCT (tag: 1.0)
* Zendo: https://xxxx

For the installation and usage of the RestCT tool, please see `install.md` file. The Swagger specifications are all in JSON format, which can be handled in a simple text editor.

The directories of this artifcat are organised as follows:

* 1
* 2
* 3



## Replicate the Experiment

In the experiment, RestCT is applied to test APIs of two service systems, GitLab (a local version is deployed as GitLab is an open source project) and Bing Maps (the remote service is used as the subject).



### Test GitLab (6 APIs)

The Docker environment is required to deploy GitLab. So, please deploy the docker image of specified version at first:

```bash
sudo docker run --detach \
    --hostname gitlab.example.com \
    --publish 30001:443 --publish 30000:80 --publish 30002:22 \
    --name gitlab \
    --restart always \
    --volume /srv/gitlab/config:/etc/gitlab \
    --volume /srv/gitlab/logs:/var/log/gitlab \
    --volume /srv/gitlab/data:/var/opt/gitlab \
    gitlab/gitlab-ce: 13.10.3-ce.0
```
To publish a port for container, we use `--publish` flag on the docker run command. The format of the `--publish` command is `[host port]:[container port]`. 
So if we want the base url of the API to be same as described in the swagger, we have to expose port 80 inside the container to port 30000 outside the container, `--publish 30000:80`.

Next, Authentication Configuration. We use an **OAuth2 token** to authenticate with the API by passing it in the `Authorization` header. 

enter in GitLab container already running healthily
```bash
sudo docker exec -it gitlab /bin/bash
```
log in to GitLab console
```bash
gitlab-rails console
```
set account and password
```bash
user = User.where(id:1).first
user.password = 'YOUR_PASSWORD'
user.password_confirmation = 'YOUR_PASSWORD'
user.save!
```
now, we get the administrator account information, then we request an `access_token` with HTTP request
```python
# python
import requests

account = {
          "grant_type": "password",
          "username": "admin@example.com",
          "password": "YOUR_PASSWORD"
        }

header = {'Content-Type': 'application/json'}

# the baseurl depends on `[host port]:80` passed to `--publish` flag
# the default is http://localhost:30000/
oauth = requests.post('http://localhost:30000/oauth/token', json=account, headers=header)

oauth.json()
```
Example response:
```python
{
 "access_token": "de6780bc506a0446309bd9362820ba8aed28aa506c71eedbe1c5c4f9dd350e54",
 "token_type": "bearer",
 "expires_in": 7200,
 "refresh_token": "8257e65c97202ed1726cf9571600918f3bffb2544b26e00a61df9897668c33a1",
 "created_at": 1607635748
}
```
Example of using the `OAuth2 token` in a header
```bash
curl --header "Authorization: Bearer OAUTH-TOKEN" "https://gitlab.example.com/api/v4/projects"
```

Finally, run the following command to use RestCT to test each subject API of GitLab:

```bash
python replicate_gitlab.py [subject] [coverage]
```

* `subject` indicates the name of the subject API, which can be `branch`, `projects`, ...
* `coverage` 

Once the execution finishes, statistics of the testing results will be printed in the stdout (from which the data reported in the paper can be extracted). An additional data file `[subject].csv` will also be produced.

**Note**: it will take about one hour to test each subject API.



### Test BingMaps (5 APIs)

We rely on the remote service of Bing Maps to perform testing. So, please register at [Bing Maps Dev Center](https://www.bingmapsportal.com/) and apply an API key at first. The specific steps are:
- Sign in to the Bing Maps Dev Center with your Microsoft Account.
- Go to “My Account” and click on “My Keys.”
- Fill out the form and click “Create” and get your API key details.

Similarly, run the following command to use RestCT to test each subject API of Bing Maps:

```bash
python replicate_bingmaps.py [subject] [coverage]
```

* `subject` indicates the name of the subject API, which can be ...
* `coverage` 

Once the execution finishes, statistics of the testing results will be printed in the stdout (from which the data reported in the paper can be extracted). An additional data file `[subject].csv` will also be produced.

**Note**: it will take about one hour to test each subject API.



#### Experimental Data

After the testing of each subject API, the stdout will print the following data ():

* The number of operation sequences generated
* The average length of all operation sequences
* ...

The `subject.csv` file ...

