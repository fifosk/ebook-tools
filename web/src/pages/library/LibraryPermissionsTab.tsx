import type { AccessPolicy, AccessPolicyUpdatePayload } from '../../api/dtos';
import AccessPolicyEditor from '../../components/access/AccessPolicyEditor';
import styles from '../LibraryPage.module.css';

type LibraryPermissionsTabProps = {
  policy: AccessPolicy | null | undefined;
  ownerId?: string | null;
  canEdit: boolean;
  onSave: (payload: AccessPolicyUpdatePayload) => Promise<void>;
};

export default function LibraryPermissionsTab({
  policy,
  ownerId,
  canEdit,
  onSave,
}: LibraryPermissionsTabProps) {
  return (
    <div className={styles.tabContent}>
      <AccessPolicyEditor
        policy={policy}
        ownerId={ownerId}
        defaultVisibility="public"
        canEdit={canEdit}
        onSave={onSave}
        title="Sharing"
      />
    </div>
  );
}
