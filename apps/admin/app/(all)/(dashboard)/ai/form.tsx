/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Controller, useForm } from "react-hook-form";
import { Lightbulb } from "lucide-react";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type {
  IFormattedInstanceConfiguration,
  TInstanceAIConfigurationKeys,
} from "@plane/types";
import { CustomSelect } from "@plane/ui";
// components
import type { TControllerInputFormField } from "@/components/common/controller-input";
import { ControllerInput } from "@/components/common/controller-input";
// hooks
import { useInstance } from "@/hooks/store";

type IInstanceAIForm = {
  config: IFormattedInstanceConfiguration;
};

type AIFormValues = Record<TInstanceAIConfigurationKeys, string>;

type TProviderKey = "openai" | "anthropic" | "yandex" | "gigachat" | "custom";

const PROVIDER_OPTIONS: Record<TProviderKey, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  yandex: "YandexGPT (Yandex Cloud)",
  gigachat: "GigaChat (Sber)",
  custom: "Custom (OpenAI-compatible)",
};

type TProviderPreset = {
  baseUrl: string;
  modelPlaceholder: string;
};

const PROVIDER_PRESETS: Record<TProviderKey, TProviderPreset> = {
  openai: { baseUrl: "", modelPlaceholder: "gpt-4o-mini" },
  anthropic: { baseUrl: "", modelPlaceholder: "claude-3-sonnet-20240229" },
  yandex: {
    baseUrl: "https://llm.api.cloud.yandex.net/v1",
    modelPlaceholder: "yandexgpt/latest",
  },
  gigachat: {
    baseUrl: "https://gigachat.devices.sberbank.ru/api/v1",
    modelPlaceholder: "GigaChat",
  },
  custom: { baseUrl: "", modelPlaceholder: "model-name" },
};

const isProviderKey = (value: string): value is TProviderKey =>
  value in PROVIDER_OPTIONS;

export function InstanceAIForm(props: IInstanceAIForm) {
  const { config } = props;
  // store
  const { updateInstanceConfigurations } = useInstance();
  // form data
  const {
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<AIFormValues>({
    defaultValues: {
      LLM_PROVIDER: config["LLM_PROVIDER"] || "openai",
      LLM_API_KEY: config["LLM_API_KEY"],
      LLM_MODEL: config["LLM_MODEL"],
      LLM_BASE_URL: config["LLM_BASE_URL"],
      LLM_FOLDER_ID: config["LLM_FOLDER_ID"],
      GIGACHAT_SCOPE: config["GIGACHAT_SCOPE"] || "GIGACHAT_API_PERS",
      LLM_TLS_VERIFY: config["LLM_TLS_VERIFY"] || "1",
    },
  });

  const rawProvider = watch("LLM_PROVIDER") || "openai";
  const provider: TProviderKey = isProviderKey(rawProvider)
    ? rawProvider
    : "openai";
  const preset = PROVIDER_PRESETS[provider];

  const handleProviderChange = (
    value: TProviderKey,
    onChange: (value: string) => void,
  ) => {
    onChange(value);
    // Prefill the OpenAI-compatible base url with the provider preset so the
    // admin does not have to remember the Russian provider endpoints.
    setValue("LLM_BASE_URL", PROVIDER_PRESETS[value].baseUrl);
  };

  // Model field description differs per provider.
  const modelDescription = (() => {
    if (provider === "yandex") {
      return (
        <>
          Enter a short model name (<code>yandexgpt/latest</code>,{" "}
          <code>yandexgpt-lite/latest</code>) — it is expanded to{" "}
          <code>gpt://&lt;folder&gt;/&lt;model&gt;</code> using the folder id
          below. A full <code>gpt://</code> URI is also accepted.
        </>
      );
    }
    if (provider === "gigachat") {
      return (
        <>
          GigaChat model name, for example <code>GigaChat</code>,{" "}
          <code>GigaChat-Pro</code> or <code>GigaChat-Max</code>.
        </>
      );
    }
    if (provider === "custom") {
      return (
        <>The model identifier expected by your OpenAI-compatible endpoint.</>
      );
    }
    return (
      <>
        Choose an engine.{" "}
        <a
          href="https://platform.openai.com/docs/models/overview"
          target="_blank"
          className="text-accent-primary hover:underline"
          rel="noreferrer"
          aria-label="OpenAI models documentation"
        >
          Learn more
        </a>
      </>
    );
  })();

  // API key field description differs per provider.
  const apiKeyDescription = (() => {
    if (provider === "yandex") {
      return (
        <>
          Yandex Cloud → create an API key for a service account holding the{" "}
          <code>ai.languageModels.user</code> role (Yandex Cloud console →
          Service accounts).
        </>
      );
    }
    if (provider === "gigachat") {
      return (
        <>
          GigaChat authorization key (client credentials). Get it at{" "}
          <a
            href="https://developers.sber.ru/portal/products/gigachat-api"
            target="_blank"
            className="text-accent-primary hover:underline"
            rel="noreferrer"
            aria-label="GigaChat API documentation"
          >
            developers.sber.ru
          </a>
          . It is exchanged server-side for a short-lived access token.
        </>
      );
    }
    if (provider === "custom") {
      return (
        <>
          The API key / bearer token accepted by your OpenAI-compatible
          endpoint.
        </>
      );
    }
    return (
      <>
        You will find your API key{" "}
        <a
          href="https://platform.openai.com/api-keys"
          target="_blank"
          className="text-accent-primary hover:underline"
          rel="noreferrer"
          aria-label="OpenAI API keys page"
        >
          here.
        </a>
      </>
    );
  })();

  const aiFormFields: TControllerInputFormField[] = [
    {
      key: "LLM_MODEL",
      type: "text",
      label: "LLM Model",
      description: modelDescription,
      placeholder: preset.modelPlaceholder,
      error: Boolean(errors.LLM_MODEL),
      required: false,
    },
    {
      key: "LLM_API_KEY",
      type: "password",
      label: "API key",
      description: apiKeyDescription,
      placeholder: "sk-asddassdfasdefqsdfasd23das3dasdcasd",
      error: Boolean(errors.LLM_API_KEY),
      required: false,
    },
  ];

  // Base url is only relevant for the OpenAI-compatible presets and custom.
  const showBaseUrl =
    provider === "yandex" || provider === "gigachat" || provider === "custom";
  const showFolderId = provider === "yandex";
  const showScope = provider === "gigachat";
  const showTlsVerify = provider === "gigachat" || provider === "custom";

  const extraFormFields: TControllerInputFormField[] = [];
  if (showBaseUrl) {
    extraFormFields.push({
      key: "LLM_BASE_URL",
      type: "text",
      label: "Base URL",
      description: (
        <>
          OpenAI-compatible endpoint. Prefilled from the selected provider;
          override if you self-host.
        </>
      ),
      placeholder: preset.baseUrl || "https://api.example.com/v1",
      error: Boolean(errors.LLM_BASE_URL),
      required: provider === "custom",
    });
  }
  if (showFolderId) {
    extraFormFields.push({
      key: "LLM_FOLDER_ID",
      type: "text",
      label: "Folder ID (Yandex Cloud)",
      description: (
        <>
          Yandex Cloud folder id used to build the{" "}
          <code>gpt://&lt;folder&gt;/&lt;model&gt;</code> identifier.
        </>
      ),
      placeholder: "b1g............",
      error: Boolean(errors.LLM_FOLDER_ID),
      required: true,
    });
  }
  if (showScope) {
    extraFormFields.push({
      key: "GIGACHAT_SCOPE",
      type: "text",
      label: "GigaChat scope",
      description: (
        <>
          One of <code>GIGACHAT_API_PERS</code> (individuals),{" "}
          <code>GIGACHAT_API_B2B</code> or <code>GIGACHAT_API_CORP</code> (legal
          entities).
        </>
      ),
      placeholder: "GIGACHAT_API_PERS",
      error: Boolean(errors.GIGACHAT_SCOPE),
      required: false,
    });
  }
  if (showTlsVerify) {
    extraFormFields.push({
      key: "LLM_TLS_VERIFY",
      type: "text",
      label: "TLS verification",
      description: (
        <>
          <code>1</code> to verify, <code>0</code> to disable, or a path to a CA
          bundle. GigaChat requires the Russian Trusted Root CA (НУЦ Минцифры) —
          download it from{" "}
          <a
            href="https://gu-st.ru/content/Other/doc/russian_trusted_root_ca.cer"
            target="_blank"
            className="text-accent-primary hover:underline"
            rel="noreferrer"
            aria-label="Russian Trusted Root CA certificate"
          >
            gu-st.ru
          </a>{" "}
          and set the path to it on the server.
        </>
      ),
      placeholder: "/etc/ssl/certs/russian_trusted_root_ca.pem",
      error: Boolean(errors.LLM_TLS_VERIFY),
      required: false,
    });
  }

  const onSubmit = async (formData: AIFormValues) => {
    const payload: Partial<AIFormValues> = { ...formData };

    await updateInstanceConfigurations(payload)
      .then(() =>
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: "Success",
          message: "AI Settings updated successfully",
        }),
      )
      .catch((err) => console.error(err));
  };

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <div>
          <div className="pb-1 text-18 font-medium text-primary">
            AI provider
          </div>
          <div className="text-13 font-regular text-tertiary">
            Choose an LLM provider and configure its credentials.
          </div>
        </div>
        <div className="grid-col grid w-full grid-cols-1 items-start justify-between gap-x-12 gap-y-8 lg:grid-cols-3">
          <div className="flex flex-col gap-1">
            <h4 className="text-13 text-tertiary">Provider</h4>
            <Controller
              control={control}
              name="LLM_PROVIDER"
              render={({ field: { value, onChange } }) => (
                <CustomSelect
                  value={value}
                  label={
                    PROVIDER_OPTIONS[(value as TProviderKey) ?? "openai"] ??
                    "Select provider"
                  }
                  onChange={(val: string) =>
                    handleProviderChange(val as TProviderKey, onChange)
                  }
                  buttonClassName="rounded-md border-subtle"
                  input
                >
                  {Object.entries(PROVIDER_OPTIONS).map(([key, label]) => (
                    <CustomSelect.Option
                      key={key}
                      value={key}
                      className="w-full"
                    >
                      {label}
                    </CustomSelect.Option>
                  ))}
                </CustomSelect>
              )}
            />
            <p className="pt-0.5 text-11 text-tertiary">
              Selecting a provider prefills its endpoint below.
            </p>
          </div>
          {aiFormFields.map((field) => (
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
          {extraFormFields.map((field) => (
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
        </div>
      </div>

      <div className="flex flex-col items-start gap-4">
        <Button
          variant="primary"
          size="lg"
          onClick={handleSubmit(onSubmit)}
          loading={isSubmitting}
        >
          {isSubmitting ? "Saving" : "Save changes"}
        </Button>

        <div className="relative inline-flex items-center gap-1.5 rounded-sm border border-accent-subtle bg-accent-subtle px-4 py-2 text-caption-sm-regular text-accent-secondary">
          <Lightbulb className="size-4" />
          <div>
            If you have a preferred AI models vendor, please get in{" "}
            <a className="font-medium underline" href="https://lokso.ru">
              touch with us.
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
