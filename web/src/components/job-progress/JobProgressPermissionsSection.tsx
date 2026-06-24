import type { AccessPolicy, AccessPolicyUpdatePayload, AccessVisibility } from '../../api/dtos';
import AccessPolicyEditor from '../access/AccessPolicyEditor';

type JobProgressPermissionsSectionProps = {
  policy: AccessPolicy | null | undefined;
  ownerId: string | null;
  defaultVisibility: AccessVisibility;
  canEdit: boolean;
  onSave?: (payload: AccessPolicyUpdatePayload) => Promise<void>;
};

export function JobProgressPermissionsSection({
  policy,
  ownerId,
  defaultVisibility,
  canEdit,
  onSave,
}: JobProgressPermissionsSectionProps) {
  return (
    <div className="job-card__section">
      <AccessPolicyEditor
        policy={policy}
        ownerId={ownerId}
        defaultVisibility={defaultVisibility}
        canEdit={canEdit}
        onSave={onSave}
      />
    </div>
  );
}
