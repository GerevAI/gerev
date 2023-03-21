
import React from 'react';

import { FaConfluence, FaSlack, FaGoogleDrive } from "react-icons/fa";

import BlueFolder from '../assets/images/blue-folder.svg';
import GoogleDoc from '../assets/images/google-doc.svg';
import GoogleDocx from '../assets/images/google-docx.svg';
import GooglePptx from '../assets/images/google-pptx.svg';


export interface TextPart{
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

  
export enum Platform {
    Confluence = "confluence",
    Slack = "slack",
    Drive = "google_drive"
}

export enum PlatformDisplayName {
    Confluence = "Confluence",
    Slack = "Slack",
    Drive = "Google Drive"
}

export interface SearchResultProps {
    title: string 
    author: string
    author_image_url: string
    author_image_data: string
    time: string
    content: TextPart[]
    score: number
    location: string
    platform: string 
    document_type: ResultType
    file_type: FileType
    url: string
}

export const SearchResult = (props: SearchResultProps) => {
    return (
        <div className="mb-4 pt-2">
            <span className="relative text-sm float-right text-white right-2 top-2">{props.score.toFixed(2)}%</span>
            <div className="flex flex-row items-start">
            {getBigIconByPlatform(props.platform as Platform, props.file_type as FileType)}
            <p className='p-2 pt-0 ml-1 text-[#A3A3A3] text-sm font-poppins'>
                <a className="text-[24px] text-[#A78BF6] text-xl font-poppins font-medium hover:underline hover:cursor-pointer" href={props.url} rel="noreferrer" target='_blank'>
                    {props.title}
                </a>
                <span className="flex flex-row text-[15px] font-medium mb-4 mt-1">
                {
                    props.document_type === ResultType.Docment && <img alt="blue-folder" className="inline-block mr-2" src={BlueFolder}></img>
                }
                <span className="ml-0 text-[#D5D5D5]">
                    {
                        props.document_type === ResultType.Message && <span>#</span>
                    }
                    {props.location} ·&thinsp;
                </span>
                <span className="flex flex-row items-center">
                    <img alt="author" className="inline-block ml-2 mr-2 h-4 rounded-xl" src={props.author_image_data ? props.author_image_data : props.author_image_url}></img>
                    <span className='capitalize'>{props.author} ·</span> 
                </span>
                <span>
                    &thinsp;Updated {getFormattedTime(props.time)}&thinsp; |&thinsp;
                </span>
                <span className="flex flex-row items-center">  
                    {getSmallIconByPlatform(props.platform as Platform)}
                    <span className="text-[#A3A3A3]">{getPlatformDisplayName(props.platform as Platform)}</span>
                </span>
                </span>
                
                {props.document_type === ResultType.Docment && 
                    <span>
                    {props.content.map((text_part, index) => {
                    return (
                        <span key={index} style={{wordBreak: 'break-word'}} className={(text_part.bold ? 'font-bold text-white' : '') + 
                            " text-md font-poppins font-medium"}>
                        {text_part.content}
                        </span>
                    )})} 
                    </span>
                }
                {props.document_type === ResultType.Message && 
                    <p className="bg-[#352C45] p-2 px-4 rounded-lg font-poppins leading-[28px] border-b-[#916CCD] border-b-2">
                    {props.content.map((text_part, index) => {
                    return (
                        <span key={index} className={(text_part.bold ? 'font-bold text-white' : '') + 
                            " fony-[14px] font-regular"}>
                        {text_part.content}
                        </span>
                    )})} 
                    </p>
                }
          </p>
        </div>
      </div>
    );
}


function getFormattedTime (time: string) {
    let date = new Date(time);
    return date.toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'});
}

function getSmallIconByPlatform(platform: Platform) {
    let classes = "inline mx-1 fill-[#A3A3A3]";
    switch (platform) {
      case Platform.Confluence:
        return <FaConfluence className={classes}></FaConfluence>
      case Platform.Slack:
        return <FaSlack className={classes}></FaSlack>
      case Platform.Drive:
        return <FaGoogleDrive className={classes}></FaGoogleDrive>
    }
}

function getBigIconByPlatform (platform: Platform, fileType: FileType) {
    let classes = "mt-2 mr-2 h-[40px] w-[40px] drop-shadow-[0_0_25px_rgba(212,179,255,0.15)]";
    let image = "";
    switch (platform) {
      case Platform.Confluence:
        image = Confluence;
        break;
      case Platform.Slack:
        image = Slack;
        break;
      case Platform.Drive:
        if (fileType === FileType.GoogleDoc) {
            image = GoogleDoc;
        }
        else if (fileType === FileType.Docx) {
            image = GoogleDocx;
        } else if (fileType === FileType.Pptx) {
            image = GooglePptx;
        }   
        break;     
    }

    return <img alt="file-type" className={classes} src={image}></img>
}

export function getPlatformDisplayName(platform: Platform) {
    switch (platform) {
      case Platform.Confluence:
        return PlatformDisplayName.Confluence
      case Platform.Slack:
        return PlatformDisplayName.Slack
      case Platform.Drive:
        return PlatformDisplayName.Drive
    }
}