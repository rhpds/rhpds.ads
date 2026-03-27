# ocp4_workload_trusted_software_factory

Ansible role to deploy Trusted Software Factory (TSF) using the tssc-cli on OpenShift.

## Description

This role deploys the Trusted Software Factory (TSF) platform, which includes:
- Red Hat Build of Keycloak (RHBK) for identity and access management
- Red Hat Trusted Artifact Signer (TAS) for artifact signing
- Red Hat Trusted Profile Analyzer (TPA) for SBOM and vulnerability analysis
- OpenShift Pipelines (Tekton) for CI/CD
- Konflux for trusted software supply chain workflows

The role uses the `tssc-cli` container image to manage the deployment via Kubernetes Jobs.

## Requirements

- OpenShift 4.18+
- Cluster admin permissions
- Cert-manager operator (can be managed by TSF or pre-installed)

## Role Variables

### Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ocp4_workload_trusted_software_factory_namespace` | `tssc` | Main TSF namespace |
| `ocp4_workload_trusted_software_factory_cli_image` | `quay.io/roming22-org/tsf` | TSSC CLI container image |
| `ocp4_workload_trusted_software_factory_cli_tag` | `latest` | TSSC CLI image tag |

### Component Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ocp4_workload_trusted_software_factory_manage_cert_manager_subscription` | `false` | Let TSF install/manage cert-manager operator (set false if already installed - typical for AgnosticV) |

### Component Namespaces

| Variable | Default | Description |
|----------|---------|-------------|
| `ocp4_workload_trusted_software_factory_tas_namespace` | `tssc-tas` | TAS namespace |
| `ocp4_workload_trusted_software_factory_konflux_namespace` | `konflux-ui` | Konflux namespace |
| `ocp4_workload_trusted_software_factory_tpa_namespace` | `tssc-tpa` | TPA namespace |
| `ocp4_workload_trusted_software_factory_keycloak_namespace` | `tssc-keycloak` | Keycloak namespace |

### Operator Channels

| Variable | Default | Description |
|----------|---------|-------------|
| `ocp4_workload_trusted_software_factory_konflux_channel` | `stable-v0.1` | Konflux operator channel (overrides default stable-v0 in installer files) |

**Note**: The Konflux channel must be overridden because the default `stable-v0` channel does not exist. The role extracts the installer files and modifies the channel before deployment.

### GitLab Integration

| Variable | Default | Description |
|----------|---------|-------------|
| `ocp4_workload_trusted_software_factory_gitlab_namespace` | `gitlab` | GitLab namespace |
| `ocp4_workload_trusted_software_factory_gitlab_group` | `tsf` | GitLab group for TSF |

**Note**: The GitLab integration expects a secret named `root-user-personal-token` in the GitLab namespace containing a `token` field with the root user's personal access token. The GitLab hostname and port are automatically derived from the route.

### Quay Integration

| Variable | Default | Description |
|----------|---------|-------------|
| `ocp4_workload_trusted_software_factory_quay_namespace` | `quay-registry` | Quay namespace |
| `ocp4_workload_trusted_software_factory_quay_admin_username` | `quayadmin` | Quay admin username |
| `ocp4_workload_trusted_software_factory_quay_organization` | `quayadmin` | Quay organization for TSF |

**Note**: The Quay integration expects a secret named `quay-admin-token` in the Quay namespace containing a `token` field with the admin token. The Quay hostname is automatically derived from the route.

### Deployment Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ocp4_workload_trusted_software_factory_deploy_timeout` | `900` | Deployment timeout in seconds |

### Keycloak Admin User Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ocp4_workload_trusted_software_factory_keycloak_realm` | `redhat-external` | Keycloak realm name used by TSF |
| `ocp4_workload_trusted_software_factory_keycloak_admin_username` | `admin` | Keycloak admin username (cluster-admin in OpenShift) |
| `ocp4_workload_trusted_software_factory_keycloak_admin_password` | `{{ common_password }}` | Keycloak admin password |
| `ocp4_workload_trusted_software_factory_keycloak_admin_email` | `admin@example.com` | Keycloak admin email address |
| `ocp4_workload_trusted_software_factory_remove_kubeadmin` | `true` | Remove kubeadmin user after Keycloak authentication is configured |

## Dependencies

None

## Example Playbook

### Basic deployment with default settings

```yaml
- name: Deploy Trusted Software Factory
  hosts: localhost
  gather_facts: false
  tasks:
    - name: Include TSF workload
      ansible.builtin.include_role:
        name: ocp4_workload_trusted_software_factory
```

### Custom deployment with custom namespaces

```yaml
- name: Deploy TSF with custom namespaces
  hosts: localhost
  gather_facts: false
  vars:
    ocp4_workload_trusted_software_factory_gitlab_namespace: gitlab-system
    ocp4_workload_trusted_software_factory_quay_namespace: quay-enterprise
    ocp4_workload_trusted_software_factory_gitlab_group: my-group
  tasks:
    - name: Include TSF workload
      ansible.builtin.include_role:
        name: ocp4_workload_trusted_software_factory
```

### Deployment with pre-installed cert-manager (default for AgnosticV)

```yaml
- name: Deploy TSF with existing cert-manager
  hosts: localhost
  gather_facts: false
  vars:
    # cert-manager is typically already installed in AgnosticV
    # Default settings work correctly:
    # - enable_cert_manager: true (TSF uses cert-manager)
    # - manage_cert_manager_subscription: false (TSF doesn't install it)
    ocp4_workload_trusted_software_factory_manage_cert_manager_subscription: false
  tasks:
    - name: Include TSF workload
      ansible.builtin.include_role:
        name: ocp4_workload_trusted_software_factory
```

## Post-Deployment Access

After successful deployment, the following information is saved to `agnosticd_user_data`:

- `tsf_keycloak_url`: Keycloak SSO URL
- `tsf_namespace`: Main TSF namespace
- `tsf_tas_namespace`: Trusted Artifact Signer namespace
- `tsf_tpa_namespace`: Trusted Profile Analyzer namespace
- `tsf_konflux_namespace`: Konflux namespace
- `tsf_keycloak_admin_username`: Keycloak admin username for TSSC realm
- `tsf_keycloak_admin_password`: Keycloak admin password for TSSC realm

### Keycloak Credentials

**Initial Admin (Master Realm):**
Keycloak initial admin credentials are stored in the secret `keycloak-initial-admin` in the `tssc-keycloak` namespace:

```bash
oc get secret keycloak-initial-admin -n tssc-keycloak -o jsonpath='{.data.username}' | base64 -d
oc get secret keycloak-initial-admin -n tssc-keycloak -o jsonpath='{.data.password}' | base64 -d
```

**TSF Realm Admin:**
The role automatically creates an admin user in the TSF realm and configures OpenShift OAuth integration. This user is granted:
- **OpenShift cluster-admin role**: Full administrative access to the OpenShift cluster
- **Keycloak authentication**: Can log into OpenShift using Keycloak SSO

By default, the kubeadmin user is removed after Keycloak authentication is configured (controlled by `ocp4_workload_trusted_software_factory_remove_kubeadmin`).

## Architecture

This role is organized into modular task files:

### Task Files

**1. `deploy_tsf.yml`** - TSF Infrastructure Deployment
- Creates all TSF resources (namespace, ServiceAccount, ClusterRoleBinding, tssc-cli pod) using separate YAML templates
- Waits for the tssc-cli pod to be running
- Extracts installer files and customizes Konflux operator channel
- Creates TSF configuration and updates cert-manager settings

**2. `configure_integrations.yml`** - External Integrations
- Configures GitLab integration (retrieves route and token, configures via tssc CLI)
- Configures Quay integration (retrieves route and token, configures via tssc CLI)

**3. `configure_authentication.yml`** - Keycloak and OpenShift OAuth
- Waits for Keycloak to be ready
- Creates an admin user in the TSF realm
- Configures OpenShift OAuth client in Keycloak
- Sets up OpenShift to use Keycloak for authentication
- Grants cluster-admin role to the Keycloak admin user
- Optionally removes kubeadmin user

**4. `workload.yml`** - Main Orchestration
- Calls `deploy_tsf.yml` to set up TSF infrastructure
- Calls `configure_integrations.yml` to configure GitLab and Quay
- Deploys TSF components via `tssc deploy` command
- Calls `configure_authentication.yml` to set up Keycloak authentication
- Saves access information to agnosticd_user_data
- Cleans up the tssc-cli pod

## Troubleshooting

### Check tssc-cli pod logs (during deployment)

```bash
oc logs -n tssc tssc-cli
```

### Manually run tssc commands

If the pod still exists, you can exec into it:
```bash
oc exec -n tssc tssc-cli -- tssc config --get
oc exec -n tssc tssc-cli -- cat /tmp/installer/charts/tssc-subscriptions/values.yaml | grep -A 5 konflux
oc exec -n tssc tssc-cli -- tssc deploy --dry-run --values-template /tmp/installer/charts/values.yaml.tpl
```

### Verify Konflux channel was modified

```bash
oc exec -n tssc tssc-cli -- grep "channel: stable-v0" /tmp/installer/charts/tssc-subscriptions/values.yaml
# Should show: channel: stable-v0.1
```

### Check Konflux subscription channel

```bash
oc get subscription konflux-operator -n konflux-operator -o jsonpath='{.spec.channel}'
```

### Verify TSF configuration

```bash
oc get configmap tssc-config -n tssc -o yaml
```

## License

Apache-2.0

## Author Information

Created by Tyrell Reddy (treddy@redhat.com)
