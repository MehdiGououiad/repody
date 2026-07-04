/** Pod Security restricted profile fragments for lab migration Jobs. */

export const RESTRICTED_POD_SECURITY = `      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault`;

export const RESTRICTED_CONTAINER_SECURITY = `          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
            runAsNonRoot: true
            runAsUser: 10001
            runAsGroup: 10001
            seccompProfile:
              type: RuntimeDefault`;
