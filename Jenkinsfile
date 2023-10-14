node {
   logRotator(numToKeepStr: '10', artifactNumToKeepStr: '10')
   stage('Cleanup Branch') {
    // Trigger: GitHub webhook whenever a branch is deleted
    // Action: Delete branch's testing channels and containers

    withCredentials([string(credentialsId: 'WALL_E_STAGING_DISCORD_BOT_TOKEN', variable: 'token')]) {
        // Parse the GitHub webhook's payload
        git 'https://github.com/CSSS/wall_e_clean_branch.git'
        sh './clear_outdated_wall_e_resources.py \"${token}\"'
    }
   }
}
