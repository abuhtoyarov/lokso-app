/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { isEmpty } from "lodash-es";
import Link from "next/link";
import { useForm } from "react-hook-form";
// plane internal packages
import { API_BASE_URL } from "@plane/constants";
import { Button, getButtonStyling } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IFormattedInstanceConfiguration, TInstanceVKAuthenticationConfigurationKeys } from "@plane/types";
// components
import { CodeBlock } from "@/components/common/code-block";
import { ConfirmDiscardModal } from "@/components/common/confirm-discard-modal";
import type { TControllerInputFormField } from "@/components/common/controller-input";
import { ControllerInput } from "@/components/common/controller-input";
import type { TControllerSwitchFormField } from "@/components/common/controller-switch";
import { ControllerSwitch } from "@/components/common/controller-switch";
import type { TCopyField } from "@/components/common/copy-field";
import { CopyField } from "@/components/common/copy-field";
// hooks
import { useInstance } from "@/hooks/store";

type Props = {
  config: IFormattedInstanceConfiguration;
};

type VKConfigFormValues = Record<TInstanceVKAuthenticationConfigurationKeys, string>;

const VK_FORM_SWITCH_FIELD: TControllerSwitchFormField<VKConfigFormValues> = {
  name: "ENABLE_VK_SYNC",
  label: "VK ID",
};

export function InstanceVKConfigForm(props: Props) {
  const { config } = props;
  // states
  const [isDiscardChangesModalOpen, setIsDiscardChangesModalOpen] = useState(false);
  // store hooks
  const { updateInstanceConfigurations } = useInstance();
  // form data
  const {
    handleSubmit,
    control,
    reset,
    formState: { errors, isDirty, isSubmitting },
  } = useForm<VKConfigFormValues>({
    defaultValues: {
      VK_CLIENT_ID: config["VK_CLIENT_ID"],
      VK_CLIENT_SECRET: config["VK_CLIENT_SECRET"],
      ENABLE_VK_SYNC: config["ENABLE_VK_SYNC"] || "0",
    },
  });

  const originURL = !isEmpty(API_BASE_URL) ? API_BASE_URL : typeof window !== "undefined" ? window.location.origin : "";

  const VK_FORM_FIELDS: TControllerInputFormField[] = [
    {
      key: "VK_CLIENT_ID",
      type: "text",
      label: "Client ID (App ID)",
      description: (
        <>
          The application id (App ID) from your{" "}
          <a
            href="https://id.vk.com/about/business"
            target="_blank"
            className="text-accent-primary hover:underline"
            rel="noreferrer"
          >
            VK ID application settings.
          </a>
        </>
      ),
      placeholder: "51234567",
      error: Boolean(errors.VK_CLIENT_ID),
      required: true,
    },
    {
      key: "VK_CLIENT_SECRET",
      type: "password",
      label: "Client secret (optional)",
      description: (
        <>
          The token exchange uses PKCE, so VK ID does not require a secret. Store your{" "}
          <a
            href="https://id.vk.com/about/business"
            target="_blank"
            className="text-accent-primary hover:underline"
            rel="noreferrer"
          >
            service key
          </a>{" "}
          here for completeness if your app has one.
        </>
      ),
      placeholder: "0f9e8d7c6b5a49382716052413f2e1d0",
      error: Boolean(errors.VK_CLIENT_SECRET),
      required: false,
    },
  ];

  const VK_SERVICE_FIELD: TCopyField[] = [
    {
      key: "Callback_URI",
      label: "Callback URI",
      url: `${originURL}/auth/vk/callback/`,
      description: (
        <>
          We will auto-generate this. Paste this into the <CodeBlock darkerShade>Redirect URL</CodeBlock> field of your
          app{" "}
          <a
            href="https://id.vk.com/about/business"
            target="_blank"
            className="text-accent-primary hover:underline"
            rel="noreferrer"
            aria-label="VK ID application settings"
          >
            here.
          </a>
        </>
      ),
    },
  ];

  const onSubmit = async (formData: VKConfigFormValues) => {
    const payload: Partial<VKConfigFormValues> = { ...formData };

    try {
      const response = await updateInstanceConfigurations(payload);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Done!",
        message: "Your VK ID authentication is configured. You should test it now.",
      });
      reset({
        VK_CLIENT_ID: response.find((item) => item.key === "VK_CLIENT_ID")?.value,
        VK_CLIENT_SECRET: response.find((item) => item.key === "VK_CLIENT_SECRET")?.value,
        ENABLE_VK_SYNC: response.find((item) => item.key === "ENABLE_VK_SYNC")?.value,
      });
    } catch (err) {
      console.error(err);
    }
  };

  const handleGoBack = (e: React.MouseEvent<HTMLAnchorElement, MouseEvent>) => {
    if (isDirty) {
      e.preventDefault();
      setIsDiscardChangesModalOpen(true);
    }
  };

  return (
    <>
      <ConfirmDiscardModal
        isOpen={isDiscardChangesModalOpen}
        onDiscardHref="/authentication"
        handleClose={() => setIsDiscardChangesModalOpen(false)}
      />
      <div className="flex flex-col gap-8">
        <div className="grid w-full grid-cols-2 gap-x-12 gap-y-8">
          <div className="col-span-2 flex flex-col gap-y-4 pt-1 md:col-span-1">
            <div className="pt-2.5 text-18 font-medium">VK-provided details for Локсо</div>
            {VK_FORM_FIELDS.map((field) => (
              <ControllerInput
                key={field.key}
                control={control}
                type={field.type}
                name={field.key}
                label={field.label}
                description={field.description}
                placeholder={field.placeholder}
                error={field.error}
                required={field.required}
              />
            ))}
            <ControllerSwitch control={control} field={VK_FORM_SWITCH_FIELD} />
            <div className="flex flex-col gap-1 pt-4">
              <div className="flex items-center gap-4">
                <Button
                  variant="primary"
                  size="lg"
                  onClick={(e) => void handleSubmit(onSubmit)(e)}
                  loading={isSubmitting}
                  disabled={!isDirty}
                >
                  {isSubmitting ? "Saving" : "Save changes"}
                </Button>
                <Link href="/authentication" className={getButtonStyling("secondary", "lg")} onClick={handleGoBack}>
                  Go back
                </Link>
              </div>
            </div>
          </div>
          <div className="col-span-2 md:col-span-1">
            <div className="flex flex-col gap-y-4 rounded-lg bg-layer-1 px-6 pt-1.5 pb-4">
              <div className="pt-2 text-18 font-medium">Локсо-provided details for VK</div>
              {VK_SERVICE_FIELD.map((field) => (
                <CopyField key={field.key} label={field.label} url={field.url} description={field.description} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
