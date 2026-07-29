@description('Azure region')
param location string = resourceGroup().location

@description('Deployed backend container image')
param containerImage string

@secure()
@description('PostgreSQL administrator password')
param postgresPassword string

@secure()
@description('Rotated Dexcom client secret')
param dexcomClientSecret string

@secure()
@description('Fernet token encryption key')
param tokenEncryptionKey string

param dexcomClientId string
param dexcomRedirectUri string
param namePrefix string = 'glucoguide'

var uniqueSuffix = uniqueString(resourceGroup().id)
var postgresName = '${namePrefix}-pg-${uniqueSuffix}'
var keyVaultName = take('${namePrefix}-kv-${uniqueSuffix}', 24)

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-logs'
  location: location
  properties: {
    retentionInDays: 30
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-environment'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspace.properties.customerId
        sharedKey: workspace.listKeys().primarySharedKey
      }
    }
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: postgresName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: 'glucoguideadmin'
    administratorLoginPassword: postgresPassword
    version: '17'
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: 'glucoguide'
}

resource allowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource vault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enablePurgeProtection: true
    softDeleteRetentionInDays: 90
    sku: {
      family: 'A'
      name: 'standard'
    }
  }
}

resource apiIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-api-identity'
  location: location
}

resource keyVaultRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, apiIdentity.id, 'key-vault-secrets-user')
  scope: vault
  properties: {
    principalId: apiIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '4633458b-17de-408a-b874-0445c86b69e6'
    )
  }
}

resource dexcomSecret 'Microsoft.KeyVault/vaults/secrets@2024-11-01' = {
  parent: vault
  name: 'dexcom-client-secret'
  properties: {
    value: dexcomClientSecret
  }
}

resource encryptionSecret 'Microsoft.KeyVault/vaults/secrets@2024-11-01' = {
  parent: vault
  name: 'token-encryption-key'
  properties: {
    value: tokenEncryptionKey
  }
}

resource databaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2024-11-01' = {
  parent: vault
  name: 'database-url'
  properties: {
    value: 'postgresql+asyncpg://glucoguideadmin:${postgresPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/glucoguide'
  }
}

resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-api'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${apiIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: databaseUrlSecret.properties.secretUri
          identity: apiIdentity.id
        }
        {
          name: 'dexcom-client-secret'
          keyVaultUrl: dexcomSecret.properties.secretUri
          identity: apiIdentity.id
        }
        {
          name: 'token-encryption-key'
          keyVaultUrl: encryptionSecret.properties.secretUri
          identity: apiIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: containerImage
          env: [
            {
              name: 'ENVIRONMENT'
              value: 'production'
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'DEXCOM_ENVIRONMENT'
              value: 'production'
            }
            {
              name: 'DEXCOM_CLIENT_ID'
              value: dexcomClientId
            }
            {
              name: 'DEXCOM_CLIENT_SECRET'
              secretRef: 'dexcom-client-secret'
            }
            {
              name: 'DEXCOM_REDIRECT_URI'
              value: dexcomRedirectUri
            }
            {
              name: 'TOKEN_ENCRYPTION_KEY'
              secretRef: 'token-encryption-key'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
  dependsOn: [
    keyVaultRole
  ]
}

output apiHostname string = api.properties.configuration.ingress.fqdn
