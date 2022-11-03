## Project Introduction

Neuroglancer is a WebGL-based application written in typescript. Node.js is required to test and build the project. Check [the readme file](https://github.com/ActiveBrainAtlasPipeline/neuroglancer#building) for detailed steps.

The project is forked from [google/neuroglancer](https://github.com/google/neuroglancer). We regularly merge the upstream code into our repository. Our forked version has several customized features maintained by ourselves. We group the customizations into different branches, and we merge everything into the main branch, which is used to build the project.

We have our own database, a Django database [portal](https://activebrainatlas.ucsd.edu/activebrainatlas/admin/) and an [API](https://activebrainatlas.ucsd.edu/activebrainatlas/) for storing and loading data. Most of code for accessing our database/backend APIs are in the `src/neuroglancer/services` folder.
In addition, we recently started using a cloud database (firebase) for real-time multi-user sharing.

Note that the application also has a backend itself, used to do the computations via the rpc calls. The code talking to the neuroglancer backend usually resides in `backend.ts` files. Those files is not related to our database portal nor the backend APIs. Please do not get confused by its name.

## Code Structure
The original version of neuroglancer comes with a typescript web application and a python interface. However, we are not actively maintaining the python interface. Most of the code we are using and changing is in `src/neuroglancer`. A brief description of each folder in the repository is below.

- .github

  This is related to github workflow which is previously used for automatic checks. We are not using it actively as we now have a credential file maintained separately and the incompleteness fails all the checks. We should bring this back when we find a better way of managing the credential files.

- config

  This folder contains the build configs used by Node.js. We have not modified this yet, but it might need to be modified if we change our ways of managing credential files.

- dist

  This folder will only appear after we test or build the project. Refer to the [Testing and Deployment](#Testing-and-Deployment) section for more details

- examples

  This folder is created by upstream. We do not change it.

- ngauth_server

  This folder is only used for accessing non-public Google Cloud Storage (GCS) buckets. We are not using this option currently.

- node_modules

  This folder is automatically generated after you install the node modules. No change is needed unless there is some incompatibility.
 
- python

  This folder contains the python interface for neuroglancer. We are not actively using nor maintaining it. The interface may not even be working as we have several changes in the typescript code that are not reflected here.

- src

  This folder contains the typescript code for neuroglancer. We will be mainly working on this folder. A few sub-folders we are actively working on are

  - annotation
  
    Provides the functionalities for annotating the images. The annotation tool is one of our most frequently used tools. Its `index.ts` contains the definitions of most classes and interfaces.

  - services

    Contains the APIs to read from and write to our databases. Please note that since the `firebase.ts` contains the credentials for accessing the firebase, we excluded it from the git repository.

  - ui

    Contains the code related to the User Interface. 
  
    Most of the widgets (i.e. different components in the page) are defined in the files (classes) in `src/neuroglancer/widgets` folder. Those classes usually has an `elements` attribute, which contains the corresponding `HTMLElement` object. The class objects are usually initialized in the files in the `ui` folder; its `elements` also get inserted into the HTML here as well.

  - util

    Contains the utility functions (conversion, rotation, HTTP requests, etc).

  - widget

    Contains the code for the widget definitions. Note that neuroglancer does not use a front-end framework like Vue.js, and all of the HTMLElements are generated by `document.createElement`. Several useful widgets (`makeIcon`, etc.) are defined here.

  - Files in this directory

    Two files are especially worth noting here: `status.ts` and `viewer.ts`.

    The `status.ts` contains the utility functions to display status messages. Please note that we modified this file to make the messages easier to notice by displaying messages on the top part of the page.

    The `viewer.ts` is kind of the actual 'entry point'. You can check the `Viewer` class to see how everything gets initialized.

- templates

  This folder is created by upstream. We do not change it.

- testdata

  This folder is created by upstream. We do not change it.

- third_party

  This folder is created by upstream. We do not change it.

- typings

  This folder is created by upstream used for type-checking. We do not change it.

## Mechanisms and (Forked) Project History

Almost everything in the application can be represented by a `state`. A `state` is a JSON object with all information of in the web application, which can be used to reconstruct the page. To access the state, one can click the `{}` button on the top-right of the page. Originally, the state is encoded as the [hash](https://developer.mozilla.org/en-US/docs/Web/API/URL/hash) property of the URL, and is updated whenever a move is done by the user; when the application detects a location change (i.e. when user opens a new page with the URL), it will automatically restore the state from the hash.
The good thing about it is that, one can share the exact status of the web application by sending the URL to another person. However, the bad thing is that the URL is usually too long (thousands of characters), and pasting the link in an email even corrupts the email layout (as in Gmail).

To resolve this, we name and store the states in our database. One important contribution from our previous student, Litao Qiao, is that he created a widget in the application allowing logged-in users to store the states to the database as well as making updates (`src/neuroglancer/state_loader.ts`). We further improve it so that, the application can now read the state from the database if a given `id` is provided, so now we can share the states by a really short url. Given the great properties of state, we also implemented a real-time sharing feature, where logged-in users can write real-time to firebase, a real-time cloud database, and any other users in the multi-user mode will be able to see the same change. The code related to loading and storing the states are in `src/neuroglncer/ui/url_hash_binding.ts`.

## Features and Branches
We currently maintain 5 branches. Below are the brief descriptions of these branches.

- backend

  This branch contains everything about talking to the backend APIs. Related features are: Log-in, displaying user information, storing and loading states, multi-uesr mode, loading and applying transformation matrixs from backend (used for brain alignment), importing annotation layers stored in our database.

- customized_key_binding

  We modified a few key-bindings for the operations in the neuroglancer (e.g. closing a tab, toggling tab visibility). Those changes are in this branch.

- histogram

  Per the team's request, we added a log-scaled histogram under the original histogram (`rendering` tab of image layers).

- notifications

  We modified the position of notification messages to make it more noticeable.

- misc

  This branch contains the miscellaneous changes. Refer to the commit messages.

- deprecated/matrix

  Contains deprecated code for another way (manual way) of adjusting matrix transformation. We do not use it anymore but we keep it in this branch in case we need it in the future.

## Testing and Deployment

After setting up Node.js (Refer to [the readme file](https://github.com/ActiveBrainAtlasPipeline/neuroglancer#building) for the steps), we can run the following commands to test and/or build the project.

### Test

`npm run dev-server` builds the test version of the project and automatically host it on `localhost:8080`. While the process is running, you can make changes to any file and the pages will reload with the newest changes whenever you save a file. You can test the project locally by visiting `http://localhost:8080` aka `http://127.0.0.1:8080/`. Note that due to CORS, we will not be able to test user-related features, i.e. any feature that requires a logged in user. However, the features like loading state from database, importing annotation and applying transformation should work. You should also be able to access the human-readable code when inspecting and debugging the application. To inspect the code in Chrome, press F12.

The generated files will reside in `dist/dev` folder. You can `scp` this folder to the server to have it deployed on the server, where you can test the user-related features. `

### Production

`npm run build-min` builds the production version. The code will be compressed in the generated files. Those files are in the `dist/min` folder. You can `scp` this folder to deploy the application to production.