# Migration to remove the CVEDerivationClusterProposalNotificationChannel pgpubsub trigger.
# This trigger is no longer needed because notifications are now created
# synchronously inside cache_new_suggestions() after the cache is populated,
# fixing the race condition described in issue #829.

import pgtrigger.migrations
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shared', '0070_cvederivationclusterproposal_rejection_reason'),
    ]

    operations = [
        pgtrigger.migrations.RemoveTrigger(
            model_name='cvederivationclusterproposal',
            name='pgpubsub_07e32',
        ),
    ]
