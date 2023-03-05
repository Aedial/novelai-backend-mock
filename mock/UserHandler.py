from typing import Union

from fastapi_jwt_auth import AuthJWT

from .models import (
    PriorityResponse,
    SubscriptionResponse,
    GetKeystoreResponse,
    AccountInformationResponse,
    UserAccountDataResponse,
    SubscriptionTierPerks,
    SubscriptionAvailableTrainingSteps
)
from .db import Session, User, get_user, SubscriptionTier
from .FileSystemHandler import FSHandler


class UserHandler:
    auth: AuthJWT
    user: User

    def __init__(self, auth: AuthJWT, session: Union[None, Session] = None):
        self.auth = auth
        self.user = get_user(auth, session)

    @property
    def priority(self):
        return PriorityResponse(
            maxPriorityActions = self.user.maxPriorityActions,
            nextRefillAt = self.user.nextRefillAt,
            taskPriority = self.user.taskPriority
        )

    TierPerks = {
        SubscriptionTier.TABLET: {
            "contextTokens": 1024,
            "unlimitedMaxPriority": False
        },
        SubscriptionTier.SCROLL: {
            "contextTokens":        2048,
            "unlimitedMaxPriority": False
        },
        SubscriptionTier.OPUS: {
            "contextTokens":        2048,
            "unlimitedMaxPriority": True
        }
    }

    @property
    def subscription_tier_perks(self):
        perks = self.TierPerks[self.user.tier]

        return SubscriptionTierPerks(
            maxPriorityActions = self.user.maxPriorityActions,
            startPriority = 10.0,
            **perks,
            moduleTrainingSteps = self.user.purchasedTrainingSteps + self.user.fixedTrainingStepsLeft
        )

    @property
    def context_tokens(self):
        return self.TierPerks[self.user.tier]["contextTokens"]

    @property
    def subscription_available_training_steps(self):
        return SubscriptionAvailableTrainingSteps(
            purchasedTrainingSteps = self.user.purchasedTrainingSteps,
            fixedTrainingStepsLeft = self.user.fixedTrainingStepsLeft
        )

    @property
    def subscription(self):
        return SubscriptionResponse(
            tier = self.user.tier,
            active = self.user.active,
            expiresAt = self.user.expiresAt,
            perks = self.subscription_tier_perks,
            paymentProcessorData = self.user.paymentProcessorData,
            trainingStepsLeft = self.subscription_available_training_steps
        )

    @property
    def keystore(self):
        keystore = FSHandler(self.auth).read_internal_object("keystore")

        return GetKeystoreResponse(keystore = keystore)

    @property
    def client_settings(self):
        return FSHandler(self.auth).read_internal_object("clientsettings")

    @property
    def account_information(self):
        return AccountInformationResponse(
            emailVerified = self.user.emailVerified,
            emailVerificationLetterSent = self.user.emailVerificationLetterSent,
            trialActivated = self.user.trialActivated,
            trialActionsLeft = self.user.trialActionsLeft,
            accountCreatedAt = self.user.accountCreatedAt
        )

    @property
    def user_account_data(self) -> UserAccountDataResponse:
        return UserAccountDataResponse(
            priority = self.priority,
            subscription = self.subscription,
            keystore = self.keystore,
            settings = self.client_settings,
            information = self.account_information
        )
