export enum HTMLInputType {
    TEXT = "text",
    TEXTAREA = "textarea",
    PASSWORD = "password"
}

export interface ConfigField {
    name: string
    input_type: HTMLInputType
    label: string
    placeholder: string
    value?: string
}


export interface DataSourceType {
    name: string
    display_name: string
    config_fields: ConfigField[]
    image_base64: string
    has_prerequisites: boolean
}

export interface ConnectedDataSource {
    id: number
    name: string
}

export interface IndexLocation {
    value: string
    label: string
}