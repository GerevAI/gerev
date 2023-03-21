
import React from 'react';

import BlueFolder from '../assets/images/blue-folder.svg';
import GoogleDoc from '../assets/images/google-doc.svg';
import Docx from '../assets/images/docx.svg';
import Pptx from '../assets/images/pptx.svg';
import { DataSourceType } from '../data-source';


export interface TextPart {
    content: string
    bold: boolean
}


export enum ResultType {
    Docment = "document",
    Message = "message",
    Comment = "comment",
    Person = "person"
}

export enum FileType {
    Docx = "docx",
    Pptx = "pptx",
    GoogleDoc = "doc",
}

export interface SearchResultDetails {
    type: ResultType
    data_source: string
    title: string
    author: string
    author_image_url: string
    author_image_data: string
    time: string
    content: TextPart[]
    score: number
    location: string
    file_type: FileType
    url: string
}


export interface SearchResultProps {
    resultDetails: SearchResultDetails
    dataSourceType: DataSourceType
}

export const SearchResult = (props: SearchResultProps) => {
    return (
        <div className="mb-4 pt-2">
            <span className="relative text-sm float-right text-white right-2 top-2">{props.resultDetails.score.toFixed(2)}%</span>
            <div className="flex flex-row items-start">
                {getBigIcon(props)}
                <p className='w-10/12 p-2 pt-0 ml-1 text-[#A3A3A3] text-sm font-poppins'>
                    <a className="text-[24px] text-[#A78BF6] text-xl font-poppins font-medium hover:underline hover:cursor-pointer" href={props.resultDetails.url} rel="noreferrer" target='_blank'>
                        {props.resultDetails.title}
                    </a>
                    <span className="flex flex-row text-[15px] font-medium mb-4 mt-1">
                        {
                            props.resultDetails.type === ResultType.Docment && <img alt="blue-folder" className="inline-block mr-2" src={BlueFolder}></img>
                        }
                        <span className="ml-0 text-[#D5D5D5]">
                            {
                                props.resultDetails.type === ResultType.Message && <span>#</span>
                            }
                            {props.resultDetails.location} ·&thinsp;
                        </span>
                        <span className="flex flex-row items-center">
                            <img alt="author" className="inline-block ml-2 mr-2 h-4 rounded-xl" src={props.resultDetails.author_image_data ? props.resultDetails.author_image_data : props.resultDetails.author_image_url}></img>
                            <span className='capitalize'>{props.resultDetails.author} ·</span>
                        </span>
                        <span>
                            &thinsp;Updated {getFormattedTime(props.resultDetails.time)}&thinsp; |&thinsp;
                        </span>
                        <span className="flex flex-row items-center">
                            <img alt="file-type" className="inline mx-1 fill-[#A3A3A3] h-[12px] w-[12px] grayscale"
                                src={props.dataSourceType.image_base64}></img>
                            <span className="text-[#A3A3A3]">{props.dataSourceType.display_name}</span>
                        </span>
                    </span>

                    {props.resultDetails.type === ResultType.Docment &&
                        <span>
                            {props.resultDetails.content.map((text_part, index) => {
                                return (
                                    <span key={index} style={{ wordBreak: 'break-word' }} className={(text_part.bold ? 'font-bold text-white' : '') +
                                        " text-md font-poppins font-medium"}>
                                        {text_part.content}
                                    </span>
                                )
                            })}
                        </span>
                    }
                    {props.resultDetails.type === ResultType.Message &&
                        <p className="bg-[#352C45] p-2 px-4 rounded-lg font-poppins leading-[28px] border-b-[#916CCD] border-b-2">
                            {props.resultDetails.content.map((text_part, index) => {
                                return (
                                    <span key={index} className={(text_part.bold ? 'font-bold text-white' : '') +
                                        " fony-[14px] font-regular"}>
                                        {text_part.content}
                                    </span>
                                )
                            })}
                        </p>
                    }
                </p>
            </div>
        </div>
    );
}


function getFormattedTime(time: string) {
    let date = new Date(time);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getBigIcon(props: SearchResultProps) {
    let containingClasses = "";
    let containingImage = "";
    let onTopImage = "";
    switch (props.resultDetails.type) {
        case ResultType.Docment:
            if (props.resultDetails.file_type === null) {
                containingImage = props.dataSourceType.image_base64;
            } else {
                onTopImage = props.dataSourceType.image_base64;
                switch (props.resultDetails.file_type) {
                    case FileType.Docx:
                        containingImage = Docx;
                        break;
                    case FileType.Pptx:
                        containingImage = Pptx;
                        break;
                    case FileType.GoogleDoc:
                        containingImage = GoogleDoc;
                        break;
                }
            }
            break;
        case ResultType.Message:
            containingClasses = "rounded-full"
            containingImage = props.resultDetails.author_image_data ? props.resultDetails.author_image_data : props.resultDetails.author_image_url;
            onTopImage = props.dataSourceType.image_base64;
            break;
    }

    if (onTopImage !== "") {
        return (
            <div className="mt-2 mr-[10px] drop-shadow-[0_0_25px_rgba(212,179,255,0.15)]">
                <img height={"45px"} width={"45px"} className={containingClasses} alt="file-type" src={containingImage}></img>
                <img alt="file-type" className="company-logo rounded-full p-[3px] h-[24px] w-[24px] absolute -right-[5px] -bottom-[5px] bg-white" src={onTopImage}></img>
            </div>
        )
    } else {
        return <img alt="file-type" className="mt-2 mr-2 h-[40px] w-[40px] drop-shadow-[0_0_25px_rgba(212,179,255,0.15)]" src={containingImage}></img>
    }
}
